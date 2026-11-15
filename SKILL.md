---
name: daily-course-site
description: 生成按天推进的纯本地课程学习网站，或为这类站点新增可插拔教学组件。当用户要求把教材、公开课、视频课、考纲拆成 Day 小节并配每日练习，或涉及题库设计、目录页、错题册、进度页、笔记与费曼复述、导师交接、浏览器内编程、自动保存、本地单机站时使用。提供稳定内核加题型/页面/功能三类插件的装配脚本、默认温和配色骨架与通用自检。关键词：每日学习站、打卡、Day 编排、course site、plugin、学习网站生成器。
agent_created: true
---

# 每日课程学习站生成器

## 用途

把任意课程（教材、公开课、视频课、考纲）装配成一个纯本地、按 Day 推进的学习站。站点由**稳定内核**与**可插拔组件**组成：内核只负责状态、保存、路由、每日编排与作答记录；题型、页面、笔记、错题、导师、编程实验室等能力都是独立插件，由唯一的装配清单 `site.json` 决定启停。新增能力只增加插件，不修改内核。

默认视觉采用 `mit-600-study` 的温和配色（米白底、低饱和蓝、柔绿/柔红反馈），见 `references/design-system.md`。

## 何时使用

- 要求「再做一个某课程的学习网站」「把某本教材 / 某套公开课拆成每天一节」「做每日打卡站」。
- 要求在已有站点里加一种题型、一个页面、笔记系统、导师联动、错题本、浏览器内编程等。
- 要求调整每日题量、配色、端口、课程来源，或检查这类站点的自检、自动保存、启动脚本。
- 要求总结 / 复用 `python-tutor`、`mit-600-study` 两个项目的做法。

不适用于：在线多人系统、账号与云数据库、需要发布到公网的站点。本框架只产出 `127.0.0.1` 单机站。

## 框架分层

| 层 | 内容 | 是否随课程变化 |
| --- | --- | --- |
| 装配层 | `site.json` 装配清单 + `init_course_site.py` | 每个站点一份清单 |
| 内核层 | `Site` 单例：状态与合并、自动保存、路由、每日编排、作答与错题、事件总线 | **不变** |
| 插件层 | `question-type` / `page` / `feature` 三类插件 | 按需插拔 |
| 数据层 | `course.json`、`questions.json`、`records/state.json` | 每个课程一份 |

完整契约、数据流与目录规范见 `references/architecture.md`；字段定义见 `references/data-contracts.md`；现有插件规格见 `references/plugin-catalog.md`。

## 装配流程

1. **确认需求边界**：课程来源与集数、每日时长与题量、是否需要编程题、是否需要导师联动、端口。课程事实（版本、链接、译名）须先核实并标注日期，见 `references/lessons-learned.md`。
2. **读取骨架**：`assets/skeleton/` 内含 `core/`（内核、`theme.css`、通用服务端）、`plugins/`（默认插件目录）、`plugins.json`（插件元数据）、`site.example.json`、`data/*.example.json`、`records/HANDOFF.template.md`。
3. **编写 `site.json`**：从 `site.example.json` 复制，填写 `name`、`port`、`plugins`、`quota`、`dailyMinutes`。只启用实际需要的插件。
4. **填充课程与题库**：在目标目录 `data/course.json` 与 `data/questions.json` 中填写内容。题目只使用本讲及此前讲次的概念；每题带 `concept`，供超纲校验使用。
5. **装配**：执行 `python scripts/init_course_site.py --target <目标目录> --site <site.json>`。脚本复制内核、按清单复制插件、生成页面与 `assets/data/*.js`、`server.py`、`start.bat`、`records/` 模板。
6. **自检**：执行 `python scripts/verify_site.py --target <目标目录>`。检查插件完整性、题型覆盖、题量、答案合法性、概念超纲、页面引用、`start.bat` 编码与服务端冒烟。
7. **启动实测**：在真实 cmd 环境启动 `start.bat --no-browser`，访问 `/api/health` 与首页，确认返回 200，再清理进程。
8. **交付**：记录启动方式、自检结果、未提交状态。未经明确指令不 commit / push、不发布。

## 新增插件

- **复用型**：在 Skill 骨架 `assets/skeleton/plugins/<id>/client.js` 写注册调用，并在 `assets/skeleton/plugins.json` 登记。
- **单站型**：在目标站 `plugins/<id>/client.js` 写注册调用，并在目标站 `plugins.json` 登记；装配时本地实现优先，同名条目覆盖骨架。

两种方式都只需要在 `site.json` 的 `plugins` 列表加入 id，然后重跑装配与 `verify_site.py`，**不改动 `core/core.js`**。元数据字段见 `references/data-contracts.md` §5，注册签名与钩子点见 `references/architecture.md` §5–§7。插件可同时贡献多个能力（例如 `q-code` 与 `page-playground` 配套提供编程题型和实验室页面）。

## 硬性约束

- `records/state.json` 是唯一事实源；`HANDOFF.md` 只放教学上下文，其余文件只放指针，不复制当前进度。
- 服务端必须按记录身份合并写入，禁止用空白状态覆盖已有作答。
- 文本输入 250ms 防抖自动落盘，页面隐藏 / 关闭时强制同步，并镜像到 `records/drafts.md`。
- `start.bat` 必须是 CRLF 换行且纯 ASCII，失败时 `pause` 显示原因；不得静默退出。
- 讲解与解析使用结构完整的陈述句，不堆碎片短句、不乱用比喻。
- 对外文字（README、博客、简历）只写事实、规格、做法，不夸大、不追加感悟段落。
- 默认纯本地；新增文件不等于发布。

## 资源

| 路径 | 用途 |
| --- | --- |
| `references/architecture.md` | 内核职责、插件契约、数据流、目录规范 |
| `references/plugin-catalog.md` | 默认插件清单、规格、开关与两站对应关系 |
| `references/data-contracts.md` | `site.json` / 课程 / 题库 / 状态 / 插件元数据字段 |
| `references/design-system.md` | 温和配色 token、版式、主题替换方法 |
| `references/lessons-learned.md` | 两个已建成站点的经验与踩坑清单 |
| `scripts/init_course_site.py` | 按 `site.json` 装配完整站点 |
| `scripts/verify_site.py` | 通用自检（含启动脚本编码与服务端冒烟） |
| `assets/skeleton/` | 可运行骨架、默认插件、配置与数据样例 |
