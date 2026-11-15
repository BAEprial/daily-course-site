# -*- coding: utf-8 -*-
"""按 site.json 装配一个每日课程学习站。

用法：
  python init_course_site.py --target <目标目录> [--site <site.json>] [--example] [--force]

装配只读骨架，不修改内核与插件源码；生成物可重复重建。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import shutil
import sys

SKILL_ROOT = pathlib.Path(__file__).resolve().parent.parent
SKELETON = SKILL_ROOT / "assets" / "skeleton"

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{label} · {name}</title>
<link rel="stylesheet" href="assets/app.css">
</head>
<body data-page="{route}">
<header class="top">
  <div class="top-inner">
    <a class="brand" href="index.html">{short}</a>
    <nav class="nav">
{nav}
    </nav>
    <div class="sync-pill" id="sync-pill"><span class="dot busy"></span>连接中…</div>
  </div>
</header>
<main class="wrap" id="app"></main>
<footer class="foot">
  <span>{source} · 个人学习站</span>
  <span>{copyright}</span>
</footer>
{scripts}
</body>
</html>
"""

START_BAT = """@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Daily Course Site - Local Server
echo Starting local study site...
echo.
python -V >nul 2>&1
if errorlevel 1 goto NOPY
echo Server: http://127.0.0.1:{port}/
echo Keep this window open while studying. Close it to stop the server.
echo.
python server.py %*
if errorlevel 1 goto FAILED
goto END
:NOPY
echo.
echo [ERROR] Python 3 was not found in PATH.
echo Install Python 3 from https://www.python.org/downloads/
echo and check "Add python.exe to PATH", then run this file again.
echo.
pause
goto END
:FAILED
echo.
echo [ERROR] The server stopped. Read the message above.
echo If the port is already in use, try: start.bat --port {alt}
echo.
pause
goto END
:END
"""

README = """# {name}

依据 {source} 编排的本地学习站。纯本地运行，不需要账号，学习数据只留在本机。

## 启动

Windows 双击 `start.bat`，或在项目目录执行：

```bat
python server.py
```

服务默认监听 `127.0.0.1:{port}`，启动后打开浏览器。启动后的终端窗口需要保持打开，关闭窗口即停止服务。端口被占用时用 `start.bat --port {alt}`。

## 编排

- 共 {lectures} 讲，每讲对应一个 Day，每日约 {minutes} 分钟。
- 每日题量：{quota}。
- 站点由稳定内核与可插拔组件组成，装配清单为 `site.json`；启用的插件见「课程说明」页。

## 数据

| 路径 | 内容 |
| --- | --- |
| `records/state.json` | 唯一事实源：进度、作答、错题、简述、草稿 |
| `records/drafts.md` | 未点保存的输入内容，供导师读取 |
| `records/HANDOFF.md` | 教学上下文交接卡 |
| `records/teaching-log.md` | 只追加的教学日志 |
| `data/course.json` | 课程与讲次（含概念清单） |
| `data/questions.json` | 题库 |

服务端按记录身份合并写入，空白状态不会删除已有作答。文本输入 250ms 防抖自动落盘，页面隐藏或关闭时强制同步。

## 修改内容

改题目或课程后重跑装配与自检：

```bat
python tools\\build.py
python tools\\verify.py
```

不要直接编辑 `assets/data/*.js` 与页面 HTML，它们是生成物。

## 自检

`tools/verify.py` 检查插件完整性、题型覆盖、每日题量、答案合法性、概念超纲、页面引用、`start.bat` 编码与服务端冒烟。

## 版权

{copyright}
"""


def read_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def js_assign(path: pathlib.Path, varname: str, obj) -> None:
    write_text(path, "window.%s = %s;\n" % (varname, json.dumps(obj, ensure_ascii=False, indent=2)))


def order_plugins(ids: list[str], meta: dict) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    visiting: set[str] = set()

    def visit(pid: str) -> None:
        if pid in seen:
            return
        if pid in visiting:
            raise ValueError("插件依赖出现循环：" + pid)
        visiting.add(pid)
        for dep in meta[pid].get("requires", []):
            if dep not in ids:
                raise ValueError("插件 %s 依赖的 %s 未在 site.json 中启用" % (pid, dep))
            visit(dep)
        visiting.discard(pid)
        seen.add(pid)
        ordered.append(pid)

    for pid in ids:
        visit(pid)
    return ordered


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="装配每日课程学习站")
    p.add_argument("--target", required=True, help="目标站点目录")
    p.add_argument("--site", help="site.json 路径，默认 <target>/site.json")
    p.add_argument("--example", action="store_true", help="缺少 data/ 时使用骨架样例数据")
    return p


def main() -> int:
    args = build_parser().parse_args()
    target = pathlib.Path(args.target).resolve()
    target.mkdir(parents=True, exist_ok=True)

    site_path = pathlib.Path(args.site).resolve() if args.site else target / "site.json"
    if not site_path.exists():
        site_path.write_bytes((SKELETON / "site.example.json").read_bytes())
        print("已生成装配清单：" + str(site_path))
    site = read_json(site_path)
    for key in ("name", "port", "theme", "dailyMinutes", "quota", "plugins", "source"):
        if key not in site:
            raise ValueError("site.json 缺少必填字段：" + key)

    # 装配清单始终落到站点根目录，server.py 会读取它拿端口。
    if site_path != target / "site.json":
        write_text(target / "site.json", json.dumps(site, ensure_ascii=False, indent=2))

    # 插件元数据：骨架清单 + 站点本地清单（本地同名条目覆盖骨架，便于单站定制）。
    catalog = read_json(SKELETON / "plugins.json")
    local_catalog = target / "plugins.json"
    if local_catalog.is_file():
        merged: dict[str, dict] = {m["id"]: m for m in catalog}
        for m in read_json(local_catalog):
            merged[m["id"]] = m
        catalog = list(merged.values())
    meta = {m["id"]: m for m in catalog}
    missing = [pid for pid in site["plugins"] if pid not in meta]
    if missing:
        raise ValueError("plugins.json 中找不到插件：" + ", ".join(missing))
    ordered = order_plugins(site["plugins"], meta)

    # 课程与题库
    data_dir = target / "data"
    course_file, questions_file = data_dir / "course.json", data_dir / "questions.json"
    if not course_file.exists() or not questions_file.exists():
        if not args.example:
            raise ValueError("缺少 data/course.json 或 data/questions.json；首次装配可加 --example")
        data_dir.mkdir(parents=True, exist_ok=True)
        if not course_file.exists():
            course_file.write_bytes((SKELETON / "data" / "course.example.json").read_bytes())
        if not questions_file.exists():
            questions_file.write_bytes((SKELETON / "data" / "questions.example.json").read_bytes())
        print("已写入样例课程与题库，正式使用前请替换。")
    course, qdata = read_json(course_file), read_json(questions_file)

    # 目录
    for sub in ("assets/core", "assets/data", "assets/plugins", "records", "notes", "tools"):
        (target / sub).mkdir(parents=True, exist_ok=True)

    # 内核与主题
    shutil.copy2(SKELETON / "core" / "core.js", target / "assets" / "core" / "core.js")
    theme_name = site.get("theme", "warm")
    theme_file = SKELETON / "themes" / (theme_name + ".css")
    if not theme_file.exists():
        theme_file = SKELETON / "core" / "theme.css"
    css = theme_file.read_text(encoding="utf-8")
    for pid in ordered:
        rel = meta[pid]["entry"].replace("client.js", "style.css")
        extra = target / rel
        if not extra.is_file():
            extra = SKELETON / rel
        if extra.is_file():
            css += "\n/* plugin: %s */\n" % pid + extra.read_text(encoding="utf-8")
    write_text(target / "assets" / "app.css", css)
    shutil.copy2(SKELETON / "core" / "server.py", target / "server.py")

    # 插件：站点本地实现优先，否则取骨架实现。
    for pid in ordered:
        rel = meta[pid]["entry"]
        src = target / rel
        if not src.is_file():
            src = SKELETON / rel
        if not src.is_file():
            raise ValueError("插件 %s 的入口文件不存在：%s" % (pid, rel))
        dst = target / "assets" / "plugins" / pid / "client.js"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    # 配置与数据生成物
    js_assign(target / "assets" / "site-config.js", "SITE_CONFIG", site)
    js_assign(target / "assets" / "data" / "course.js", "COURSE", course)
    js_assign(target / "assets" / "data" / "questions.js", "QB", qdata)

    # 页面
    page_ids = [pid for pid in ordered if meta[pid]["kind"] == "page"]
    routes = [(pid, pid[len("page-"):] if pid.startswith("page-") else pid) for pid in page_ids]
    if not routes:
        raise ValueError("至少启用一个 page 类插件")
    wanted = site.get("pages") or [r for _, r in routes]
    label_of = {r: meta[pid].get("label", r) for pid, r in routes}
    nav_of = {r: meta[pid].get("navLabel", label_of[r]) for pid, r in routes}
    scripts = "\n".join(
        ['<script src="assets/site-config.js"></script>',
         '<script src="assets/data/course.js"></script>',
         '<script src="assets/data/questions.js"></script>',
         '<script src="assets/core/core.js"></script>'] +
        ['<script src="assets/plugins/%s/client.js"></script>' % pid for pid in ordered]
    )
    for route in wanted:
        nav = "\n".join(
            '      <a href="%s.html"%s>%s</a>' % (r, ' class="active"' if r == route else "", nav_of.get(r, r))
            for r in wanted
        )
        write_text(target / (route + ".html"), PAGE_TEMPLATE.format(
            label=label_of.get(route, route), name=site["name"], route=route,
            short=site.get("shortName", site["name"]), nav=nav, scripts=scripts,
            source=site["source"].get("name", ""), copyright=site["source"].get("copyright", "")
        ))

    # 启动脚本：CRLF + 纯 ASCII
    bat = START_BAT.format(port=site["port"], alt=site["port"] + 1)
    (target / "start.bat").write_bytes(bat.replace("\n", "\r\n").encode("ascii"))

    # 记录文件
    state_file = target / "records" / "state.json"
    if not state_file.exists():
        write_text(state_file, json.dumps({
            "version": 1, "updatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
            "progress": {}, "attempts": [], "wrongBook": [], "briefs": {},
            "drafts": {}, "notes": {}, "settings": {}
        }, ensure_ascii=False, indent=2))
    handoff = (SKELETON / "records" / "HANDOFF.template.md").read_text(encoding="utf-8")
    quota = "、".join("%s %d 题" % (k, v) for k, v in site["quota"].items())
    first = course["lectures"][0]["zh"] if course.get("lectures") else "（待填写）"
    replacements = {
        "{{SITE_NAME}}": site["name"], "{{DATE}}": dt.date.today().isoformat(),
        "{{ROOT}}": str(target), "{{START_LEVEL}}": "按课程设定填写",
        "{{DAILY_MINUTES}}": str(site["dailyMinutes"]),
        "{{COURSE_NAME}}": site["source"].get("name", site["name"]),
        "{{LECTURES}}": str(len(course.get("lectures", []))),
        "{{QUOTA}}": quota, "{{PORT}}": str(site["port"]), "{{FIRST_LECTURE}}": first,
    }
    for k, v in replacements.items():
        handoff = handoff.replace(k, v)
    if not (target / "records" / "HANDOFF.md").exists():
        write_text(target / "records" / "HANDOFF.md", handoff)
    log = target / "records" / "teaching-log.md"
    if not log.exists():
        write_text(log, "# 教学日志（append-only）\n\n> 只追加，不覆盖。每次练习或答疑后由导师追加一条。\n\n## %s · 项目建档\n\n- 依据装配清单生成站点，共 %d 讲，启用 %d 个插件。\n- 学员尚未开始 Day 1。\n" % (dt.date.today().isoformat(), len(course.get("lectures", [])), len(ordered)))
    if not (target / "records" / "drafts.md").exists():
        write_text(target / "records" / "drafts.md", "# 简述题与草稿 · 给导师\n\n（暂无）\n")
    if not (target / ".gitignore").exists():
        write_text(target / ".gitignore", "records/state.backup.json\n*.tmp\n__pycache__/\n")

    # 自检脚本与重建脚本
    shutil.copy2(SKILL_ROOT / "scripts" / "verify_site.py", target / "tools" / "verify.py")
    write_text(target / "tools" / "plugins.json", json.dumps(catalog, ensure_ascii=False, indent=2))
    write_text(target / "tools" / "build.py", (
        "# -*- coding: utf-8 -*-\n"
        "\"\"\"重新装配本站：python tools/build.py\n\n"
        "等价命令：python <skill>/scripts/init_course_site.py --target <站点目录>\n"
        "\"\"\"\n"
        "import argparse, pathlib, subprocess, sys\n"
        "p = argparse.ArgumentParser()\n"
        "p.add_argument('--skill', default=r'%s')\n"
        "a = p.parse_args()\n"
        "root = pathlib.Path(__file__).resolve().parent.parent\n"
        "script = pathlib.Path(a.skill) / 'scripts' / 'init_course_site.py'\n"
        "sys.exit(subprocess.call([sys.executable, str(script), '--target', str(root)]))\n"
    ) % str(SKILL_ROOT))

    if not (target / "README.md").exists():
        write_text(target / "README.md", README.format(
            name=site["name"], source=site["source"].get("name", "公开课程资料"),
            port=site["port"], alt=site["port"] + 1,
            lectures=len(course.get("lectures", [])), minutes=site["dailyMinutes"],
            quota=quota, copyright=site["source"].get("copyright", "课程内容版权归原作者所有。")
        ))

    print("装配完成：" + str(target))
    print("页面：" + ", ".join(r + ".html" for r in wanted))
    print("插件（%d）：" % len(ordered) + ", ".join(ordered))
    print("题目：%d 道，讲次：%d" % (len(qdata.get("questions", [])), len(course.get("lectures", []))))
    print("下一步：python tools/verify.py；然后双击 start.bat")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError) as exc:
        print("装配失败：" + str(exc), file=sys.stderr)
        sys.exit(1)
