# daily-course-site

一个 WorkBuddy 用户级 Skill，用于生成按 Day 推进的纯本地课程学习站。站点由稳定内核与可插拔组件组成：内核负责状态、自动保存、路由、每日编排、作答与错题记录；题型、页面、笔记、导师、编程实验室等能力由 `site.json` 装配清单决定启停。

产出的站点只监听 `127.0.0.1`，不依赖账号、云数据库或在线服务。

## 安装

把仓库内容放到 WorkBuddy 用户级 Skill 目录：

```
~/.workbuddy/skills/daily-course-site/
```

Windows 下对应 `C:\Users\<用户名>\.workbuddy\skills\daily-course-site\`。也可以下载 Release 中的 zip 解压到该目录。

## 目录

| 路径 | 内容 |
| --- | --- |
| `SKILL.md` | 触发条件、工作流与边界 |
| `references/` | 架构契约、插件清单、数据契约、视觉规范、踩坑清单 |
| `scripts/init_course_site.py` | 按 `site.json` 装配完整站点 |
| `scripts/verify_site.py` | 通用自检 |
| `assets/skeleton/core/` | 稳定内核：`core.js`、`server.py`、`theme.css` |
| `assets/skeleton/plugins/` | 15 个默认插件 |
| `assets/skeleton/data/` | 课程与题库样例 |
| `assets/skeleton/site.example.json` | 装配清单样例 |
| `assets/skeleton/themes/warm.css` | 默认温和配色主题 |

## 生成一个站点

需要 Python 3.9 及以上版本，仅使用标准库。

```bash
python scripts/init_course_site.py --target /path/to/new-site --example
cd /path/to/new-site
python tools/verify.py
```

Windows 下双击生成目录中的 `start.bat`，或在 cmd 中执行 `start.bat --port 8767`。服务窗口需要保持打开，关闭窗口即停止服务。

正式使用前把 `data/course.json` 与 `data/questions.json` 换成实际课程内容，并修改 `site.json` 中的名称、端口、题量与插件清单；重跑 `init_course_site.py --target <目录> --force` 后再次自检。

## 插件

三类插件通过 `Site.register()` 接入内核：

- 题型：`q-single`、`q-judge`、`q-multi`、`q-brief`、`q-code`
- 页面：`page-index`、`page-catalog`、`page-lesson`、`page-review`、`page-progress`、`page-notes`、`page-about`、`page-playground`
- 功能：`feature-mentor`、`feature-scope-lock`

`q-code` 与 `page-playground` 默认关闭，需要时在 `site.json` 中启用。新增插件可以放进本仓库的 `assets/skeleton/plugins/` 供所有站点复用，也可以只放进单个站点的 `plugins/` 目录；两种方式都不需要修改内核。元数据格式见 `assets/skeleton/plugins.json`，注册签名与钩子点见 `references/architecture.md`。

## 数据与自检

生成站的状态存于 `records/state.json`，服务端按记录身份合并写入；简述题与未提交草稿实时落盘，并镜像到 `records/drafts.md`。`tools/verify.py` 检查插件完整性、题型覆盖、题量、答案合法性、概念不超纲、页面引用、`start.bat` 编码与服务端冒烟。

本仓库不含课程原文、个人学习记录或答题数据。课程内容的版权归原作者所有。

## 本地验证记录

- 默认样例站：自检 425 项、0 问题；cmd 启动后 8 个资源返回 200；轻量 DOM 桩渲染 7 页通过。
- 插拔样例：启用 `q-code` 并新增一个站点本地题型插件后，16 个插件 / 8 个页面，自检 545 项、0 问题。
