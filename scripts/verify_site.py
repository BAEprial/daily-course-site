# -*- coding: utf-8 -*-
"""每日课程学习站通用自检。

用法：python verify_site.py [--target <站点目录>]
脚本放在站点 tools/ 下时自动以站点根目录为 target。
服务端冒烟在临时副本中执行，不触碰真实 records/。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

CHECKS = 0
ISSUES: list[str] = []


def check(cond: bool, msg: str) -> None:
    global CHECKS
    CHECKS += 1
    if not cond:
        ISSUES.append(msg)


def default_target() -> pathlib.Path:
    p = pathlib.Path(__file__).resolve()
    return p.parent.parent if p.parent.name == "tools" else pathlib.Path.cwd()


def read_json(path: pathlib.Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("无法读取 %s：%s" % (path, exc))


def section(title: str) -> None:
    print("\n=== " + title + " ===")


def check_files(root: pathlib.Path, site: dict) -> None:
    section("1. 文件与配置")
    required = [
        "site.json", "server.py", "start.bat", "README.md",
        "assets/app.css", "assets/site-config.js", "assets/core/core.js",
        "assets/data/course.js", "assets/data/questions.js",
        "records/state.json", "records/HANDOFF.md", "tools/verify.py",
    ]
    for rel in required:
        check((root / rel).is_file(), "缺少文件：" + rel)
    for key in ("name", "port", "theme", "dailyMinutes", "quota", "plugins", "source"):
        check(key in site, "site.json 缺少字段：" + key)
    check(isinstance(site.get("port"), int) and 1024 < site["port"] < 65535, "port 必须是合法端口")
    check(bool(site.get("quota")), "quota 不能为空")
    check(isinstance(site.get("plugins"), list) and site["plugins"], "plugins 不能为空")
    src = site.get("source") or {}
    check(bool(src.get("verifiedAt")), "source.verifiedAt 必须标注核实日期")
    check(bool(src.get("copyright")), "source.copyright 必须填写版权说明")


def check_plugins(root: pathlib.Path, site: dict, catalog: list) -> dict:
    section("2. 插件完整性")
    meta = {m["id"]: m for m in catalog}
    enabled = site["plugins"]
    for pid in enabled:
        check(pid in meta, "plugins.json 中没有插件：" + pid)
        if pid not in meta:
            continue
        client = root / "assets" / "plugins" / pid / "client.js"
        check(client.is_file(), "插件文件缺失：" + pid)
        if client.is_file():
            body = client.read_text(encoding="utf-8")
            check("Site.register(" in body, "插件未调用 Site.register：" + pid)
        for dep in meta[pid].get("requires", []):
            check(dep in enabled, "%s 依赖的 %s 未启用" % (pid, dep))
    # 页面与题型覆盖
    page_routes = set()
    for pid in enabled:
        if pid in meta and meta[pid]["kind"] == "page":
            page_routes.add(pid[len("page-"):] if pid.startswith("page-") else pid)
    pages = site.get("pages") or sorted(page_routes)
    for route in pages:
        check(route in page_routes, "页面 %s 没有对应的 page 插件" % route)
        check((root / (route + ".html")).is_file(), "缺少页面：" + route + ".html")
    qtypes = set()
    for pid in enabled:
        if pid in meta and meta[pid]["kind"] == "question-type":
            qtypes.add(meta[pid]["handles"])
    return {"qtypes": qtypes, "pages": pages, "meta": meta}


def check_questions(root: pathlib.Path, site: dict, ctx: dict) -> None:
    section("3. 题库与每日题量")
    qdata = read_json(root / "data" / "questions.json")
    course = read_json(root / "data" / "course.json")
    questions = qdata.get("questions", [])
    lectures = course.get("lectures", [])
    check(bool(lectures), "course.json 没有讲次")
    check(bool(questions), "questions.json 没有题目")

    ids = [q.get("id") for q in questions]
    check(len(ids) == len(set(ids)), "题目 id 存在重复")
    for q in questions:
        qid = q.get("id", "?")
        for key in ("id", "day", "type", "stem", "concept"):
            check(q.get(key) not in (None, "", []), "题目 %s 缺少 %s" % (qid, key))
        check(q.get("type") in ctx["qtypes"], "题目 %s 的题型 %s 没有对应插件" % (qid, q.get("type")))
        check(1 <= q.get("day", 0) <= len(lectures), "题目 %s 的 day 超出讲次范围" % qid)
        opts = q.get("options") or []
        ans = q.get("answer") or []
        t = q.get("type")
        if t in ("single", "judge"):
            check(len(ans) == 1, "%s：单选/判断必须有且仅有一个答案下标" % qid)
            check(all(isinstance(i, int) and 0 <= i < len(opts) for i in ans), "%s：答案下标越界" % qid)
            if t == "judge":
                check(opts == ["正确", "错误"], "%s：判断题选项应为「正确 / 错误」" % qid)
        elif t == "multi":
            check(2 <= len(ans) <= 3, "%s：多选答案应为 2–3 个" % qid)
            check(all(isinstance(i, int) and 0 <= i < len(opts) for i in ans), "%s：答案下标越界" % qid)
        elif t == "brief":
            check(ans == [], "%s：简述题不应设置自动判分答案" % qid)
            check(bool(q.get("keypoints")), "%s：简述题缺少参考要点" % qid)
        elif t == "code":
            check(bool((q.get("judge") or {}).get("expected") is not None), "%s：编程题缺少 judge.expected" % qid)
    quota = site["quota"]
    for lec in lectures:
        n = lec.get("day")
        for t, want in quota.items():
            got = len([q for q in questions if q.get("day") == n and q.get("type") == t])
            check(got == want, "Day %s 的 %s 题量为 %d，应为 %d" % (n, t, got, want))
    return course, questions


def check_scope(root: pathlib.Path, site: dict, course: dict, questions: list) -> None:
    section("4. 概念不超纲")
    if "feature-scope-lock" in site["plugins"]:
        first: dict[str, int] = {}
        for i, lec in enumerate(course.get("lectures", [])):
            for c in lec.get("concepts", []):
                first.setdefault(c, lec.get("day", i + 1))
        for c, d in (course.get("extraConcepts") or {}).items():
            first.setdefault(c, d)
        for q in questions:
            c = q.get("concept")
            check(c in first, "题目 %s 的知识点「%s」未登记在 concepts / extraConcepts" % (q.get("id"), c))
            if c in first:
                check(first[c] <= q.get("day", 0), "题目 %s 超纲：「%s」首次出现在 Day %s" % (q.get("id"), c, first[c]))
    else:
        print("（超纲锁未启用，跳过）")

    section("5. 文案完整句")
    for q in questions:
        if q.get("type") in ("brief", "code"):
            continue
        check(len(str(q.get("explain") or "")) >= 12, "题目 %s 的解析过短，需使用完整陈述句" % q.get("id"))
    for q in questions:
        check(len(str(q.get("stem") or "")) >= 8, "题目 %s 的题干过短" % q.get("id"))


def check_pages(root: pathlib.Path, pages: list) -> None:
    section("6. 页面引用")
    pat = re.compile(r'(?:src|href)="([^"]+)"')
    for route in pages:
        f = root / (route + ".html")
        if not f.is_file():
            continue
        html = f.read_text(encoding="utf-8")
        refs = [u for u in pat.findall(html) if u.startswith("assets/") or u.endswith(".html")]
        for u in refs:
            if u.startswith("http"):
                continue
            check((root / u).is_file(), "%s 引用了不存在的文件：%s" % (route + ".html", u))
        check('id="app"' in html, "%s 缺少 <main id=app>" % (route + ".html"))
        check('id="sync-pill"' in html, "%s 缺少保存状态指示" % (route + ".html"))


def check_start_bat(root: pathlib.Path) -> None:
    section("7. 启动脚本编码")
    b = (root / "start.bat").read_bytes()
    check(b.count(b"\r\n") == b.count(b"\n") and b.count(b"\n") > 0, "start.bat 必须全部使用 CRLF 换行")
    check(all(x < 128 for x in b), "start.bat 必须纯 ASCII（chcp 65001 下中文会导致行错位）")
    check(b"pause" in b, "start.bat 失败路径必须 pause 显示原因")
    check(b"python server.py %*" in b, "start.bat 必须支持参数透传")


def smoke(root: pathlib.Path) -> None:
    section("8. 服务端冒烟（临时副本）")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="dcs_smoke_"))
    try:
        dst = tmp / "site"
        shutil.copytree(root, dst, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.tmp", "notes"))
        (dst / "records" / "state.json").write_text(json.dumps({
            "version": 1, "updatedAt": "2026-01-01T00:00:00Z", "progress": {},
            "attempts": [], "wrongBook": [], "briefs": {}, "drafts": {}, "notes": {}, "settings": {}
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        proc = subprocess.Popen(
            [sys.executable, "server.py", "--port", str(port), "--no-browser"],
            cwd=str(dst), stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        base = "http://127.0.0.1:%d" % port
        try:
            up = False
            for _ in range(50):
                try:
                    with urllib.request.urlopen(base + "/api/health", timeout=0.4) as r:
                        up = r.status == 200
                        if up:
                            break
                except Exception:
                    time.sleep(0.2)
            check(up, "服务端未能启动")
            if not up:
                return
            for path, frag in (("/", b"<main"), ("/assets/app.css", b":root"), ("/assets/core/core.js", b"window.Site")):
                try:
                    with urllib.request.urlopen(base + path, timeout=3) as r:
                        body = r.read()
                        check(r.status == 200 and frag in body, "GET %s 异常" % path)
                except Exception as exc:
                    check(False, "GET %s 失败：%s" % (path, exc))
            payload = {
                "version": 1, "updatedAt": "2026-01-01T00:00:01Z",
                "progress": {}, "attempts": [{"id": "smoke-1", "day": 1, "correct": True}],
                "wrongBook": [], "briefs": {}, "drafts": {}, "notes": {}, "settings": {}
            }
            try:
                req = urllib.request.Request(base + "/api/state", data=json.dumps(payload).encode("utf-8"),
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=3) as r:
                    check(r.status == 200, "POST /api/state 返回 %s" % r.status)
                blank = dict(payload)
                blank["attempts"] = []
                req2 = urllib.request.Request(base + "/api/state", data=json.dumps(blank).encode("utf-8"),
                                              headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req2, timeout=3) as r:
                    check(r.status == 200, "空白状态 POST 失败")
                with urllib.request.urlopen(base + "/api/state", timeout=3) as r:
                    state = json.loads(r.read().decode("utf-8"))
                check(len(state.get("attempts", [])) == 1, "空白状态覆盖已有作答：合并写入规则失效")
            except Exception as exc:
                check(False, "合并写入检查失败：%s" % exc)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="每日课程学习站自检")
    ap.add_argument("--target", default=str(default_target()))
    ap.add_argument("--no-smoke", action="store_true", help="跳过服务端冒烟")
    a = ap.parse_args()
    root = pathlib.Path(a.target).resolve()
    skill_catalog = pathlib.Path(__file__).resolve().parent.parent / "assets" / "skeleton" / "plugins.json"
    candidates = [root / "tools" / "plugins.json", skill_catalog, root / "assets" / "plugins.json"]
    catalog_path = next((c for c in candidates if c.is_file()), None)
    if catalog_path is None:
        print("自检无法开始：找不到 plugins.json 插件元数据", file=sys.stderr)
        return 1
    try:
        site = read_json(root / "site.json")
        catalog = read_json(catalog_path)
    except (ValueError, OSError) as exc:
        print("自检无法开始：" + str(exc), file=sys.stderr)
        return 1

    check_files(root, site)
    ctx = check_plugins(root, site, catalog)
    check_questions_result = check_questions(root, site, ctx)
    if check_questions_result:
        course, questions = check_questions_result
        check_scope(root, site, course, questions)
    check_pages(root, ctx["pages"])
    check_start_bat(root)
    if not a.no_smoke:
        smoke(root)

    print("\n检查项：%d，问题：%d" % (CHECKS, len(ISSUES)))
    if ISSUES:
        for msg in ISSUES:
            print("  - " + msg)
        print("未通过。")
        return 1
    print("全部通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
