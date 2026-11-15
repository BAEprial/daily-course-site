# -*- coding: utf-8 -*-
"""通用本地服务：静态文件 + /api/state 合并写入 + /api/health。仅用 Python 标准库。

启动：python server.py [--port N] [--no-browser]
端口默认值从站点根目录的 site.json 读取。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import mimetypes
import os
import pathlib
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent
RECORDS = ROOT / "records"
STATE_FILE = RECORDS / "state.json"
BACKUP_FILE = RECORDS / "state.backup.json"
DRAFTS_FILE = RECORDS / "drafts.md"
SITE_FILE = ROOT / "site.json"

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


def site_port(default: int = 8766) -> int:
    try:
        return int(json.loads(SITE_FILE.read_text(encoding="utf-8")).get("port", default))
    except (OSError, ValueError, TypeError):
        return default


def blank_state() -> dict[str, Any]:
    return {
        "version": 1,
        "updatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "progress": {}, "attempts": [], "wrongBook": [],
        "briefs": {}, "drafts": {}, "notes": {}, "settings": {},
    }


def ensure_dirs() -> None:
    RECORDS.mkdir(parents=True, exist_ok=True)
    if not STATE_FILE.exists():
        atomic_write(STATE_FILE, json.dumps(blank_state(), ensure_ascii=False, indent=2))


def atomic_write(path: pathlib.Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else blank_state()
    except (OSError, ValueError):
        return blank_state()


# ---- 合并规则：空白状态不得覆盖已有数据 ----

def merge_attempts(existing: list, incoming: list) -> list:
    merged: dict[str, Any] = {}
    for item in list(existing) + list(incoming):
        if not isinstance(item, dict):
            continue
        key = str(item.get("id") or json.dumps(item, ensure_ascii=False, sort_keys=True))
        merged[key] = item
    return list(merged.values())


def merge_progress(existing: dict, incoming: dict) -> dict:
    out = dict(existing or {})
    for day, inc in (incoming or {}).items():
        if not isinstance(inc, dict):
            continue
        cur = dict(out.get(day) or {})
        ans = dict(cur.get("answers") or {})
        ans.update(inc.get("answers") or {})
        cor = dict(cur.get("correct") or {})
        cor.update(inc.get("correct") or {})
        cur["answers"], cur["correct"] = ans, cor
        cur["done"] = bool(cur.get("done") or inc.get("done"))
        if inc.get("completedAt") and not cur.get("completedAt"):
            cur["completedAt"] = inc["completedAt"]
        out[day] = cur
    return out


def merge_wrongbook(existing: list, incoming: list) -> list:
    by: dict[str, dict] = {}
    for item in list(existing) + list(incoming):
        if not isinstance(item, dict) or not item.get("qid"):
            continue
        key = str(item["qid"])
        cur = dict(by.get(key) or {})
        cur.update(item)
        cur["wrongCount"] = max(int(cur.get("wrongCount") or 0), int(item.get("wrongCount") or 0))
        by[key] = cur
    return list(by.values())


def merge_briefs(existing: dict, incoming: dict) -> dict:
    out = dict(existing or {})
    for day, inc in (incoming or {}).items():
        if not isinstance(inc, dict):
            continue
        cur = dict(out.get(day) or {})
        if str(inc.get("text") or "").strip() or not str(cur.get("text") or "").strip():
            cur.update(inc)
        else:
            cur["selfChecked"] = bool(cur.get("selfChecked") or inc.get("selfChecked"))
        out[day] = cur
    return out


def merge_nonempty(existing: dict, incoming: dict) -> dict:
    out = dict(existing or {})
    for key, value in (incoming or {}).items():
        if value or key not in out:
            out[key] = value
    return out


def merge_state(existing: dict, incoming: dict) -> dict:
    out = dict(existing or blank_state())
    out["version"] = incoming.get("version") or out.get("version") or 1
    out["updatedAt"] = incoming.get("updatedAt") or out.get("updatedAt")
    out["progress"] = merge_progress(out.get("progress") or {}, incoming.get("progress") or {})
    out["attempts"] = merge_attempts(out.get("attempts") or [], incoming.get("attempts") or [])
    out["wrongBook"] = merge_wrongbook(out.get("wrongBook") or [], incoming.get("wrongBook") or [])
    out["briefs"] = merge_briefs(out.get("briefs") or {}, incoming.get("briefs") or {})
    out["drafts"] = merge_nonempty(out.get("drafts") or {}, incoming.get("drafts") or {})
    notes = dict(out.get("notes") or {})
    notes.update(incoming.get("notes") or {})
    out["notes"] = notes
    settings = dict(out.get("settings") or {})
    settings.update(incoming.get("settings") or {})
    out["settings"] = settings
    return out


def write_drafts_md(data: dict) -> None:
    stamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [
        "# 简述题与草稿 · 给导师", "",
        "- 更新时间：" + stamp,
        "- 规则：输入框里每敲一个字都会同步到这里，不需要点击保存。",
        "- 完整明细见 `records/state.json`。", "",
        "## 一、按天的简述题答案", "",
    ]
    briefs = data.get("briefs") or {}
    any_brief = False
    for day in sorted(briefs):
        item = briefs[day] or {}
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        any_brief = True
        lines += ["### " + str(day), "", text, "",
                  "> 自评：" + ("已对照参考要点" if item.get("selfChecked") else "尚未对照参考要点"), ""]
    if not any_brief:
        lines += ["（暂无）", ""]
    lines += ["## 二、其他输入草稿", ""]
    drafts = {k: v for k, v in (data.get("drafts") or {}).items() if str(v).strip()}
    if drafts:
        for key in sorted(drafts):
            lines += ["**" + str(key) + "**", "", str(drafts[key]), ""]
    else:
        lines += ["（暂无）", ""]
    atomic_write(DRAFTS_FILE, "\n".join(lines))


class Handler(BaseHTTPRequestHandler):
    server_version = "DailyCourseSite/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")

    def _json(self, obj: Any, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        raw = self.rfile.read(length) if length else b""
        try:
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except (ValueError, UnicodeDecodeError):
            return {}

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/api/state":
            self._json(read_json(STATE_FILE))
            return
        if path == "/api/health":
            self._json({"ok": True, "service": "daily-course-site", "root": str(ROOT)})
            return
        if path == "/":
            path = "/index.html"
        rel = path.lstrip("/").replace("\\", "/")
        target = (ROOT / rel).resolve()
        try:
            target.relative_to(ROOT.resolve())
        except ValueError:
            self.send_error(403)
            return
        if not target.is_file():
            self.send_error(404)
            return
        ctype = MIME.get(target.suffix.lower()) or mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path.split("?", 1)[0] != "/api/state":
            self.send_error(404)
            return
        data = self._body()
        if not data:
            self._json({"ok": False, "error": "empty body"}, 400)
            return
        existing = read_json(STATE_FILE)
        try:
            atomic_write(BACKUP_FILE, json.dumps(existing, ensure_ascii=False, indent=2))
        except OSError:
            pass
        merged = merge_state(existing, data)
        atomic_write(STATE_FILE, json.dumps(merged, ensure_ascii=False, indent=2))
        write_drafts_md(merged)
        self._json({"ok": True, "attempts": len(merged.get("attempts") or [])})


def main() -> None:
    parser = argparse.ArgumentParser(description="每日课程学习站本地服务")
    parser.add_argument("--port", type=int, default=site_port())
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    ensure_dirs()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    url = "http://127.0.0.1:%d/" % args.port
    print("学习站已启动：" + url)
    print("数据目录：" + str(RECORDS))
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止。")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
