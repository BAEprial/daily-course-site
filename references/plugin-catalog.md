# 默认插件清单与规格

插件是目录级组件：`assets/skeleton/plugins/<id>/client.js` + `plugins.json` 中的一条元数据。启用开关在目标站 `site.json` 的 `plugins` 列表。下表来自两个已建成站点的能力拆分。

## 题型插件（`question-type`）

| id | handles | 行为 | 依赖 | 来源站点 |
| --- | --- | --- | --- | --- |
| `q-single` | `single` | 四选一，点击即判定并显示解析，选项锁定 | 无 | 两站 |
| `q-judge` | `judge` | 固定「正确 / 错误」两选项，点击即判定 | 无 | MIT 6.00 |
| `q-multi` | `multi` | 多选，选完点「提交」判定，需完全命中正确答案 | 无 | MIT 6.00 |
| `q-brief` | `brief` | 文本框作答，不自动判分；250ms 防抖落盘到 `drafts`，提供参考要点与自评勾选 | `feature-mentor` 可选 | MIT 6.00 / 费曼复述 |
| `q-code` | `code` | 浏览器内 Pyodide 执行 Python，捕获 stdout 自动判题；同时贡献 `playground` 页面 | `site.json.pyodide` | Python 私塾 |

`q-code` 的判题配置写在题目 `judge` 字段，口径见 `data-contracts.md` §3。首次加载需联网下载运行时，之后走浏览器缓存；不启用该插件的站点完全离线。

题型插件的统一要求：

- `render` 只收集答案并调用 `ctx.submit()`，不写状态、不自行保存。
- 已作答题目再次进入时显示锁定态与历史答案，允许「重做」。
- 解析必须使用完整陈述句，不堆碎片短句。
- 无自动判分的题型 `grade` 返回 `null`，但仍要调用 `ctx.submit()` 以记录作答轨迹。

## 页面插件（`page`）

| id | route | 内容 | 依赖 |
| --- | --- | --- | --- |
| `page-index` | `index` | 今日任务、统计卡片、每日时间安排、打卡入口 | 无 |
| `page-catalog` | `catalog` | 全部讲次目录、中英标题、完成状态、跳转 | 无 |
| `page-lesson` | `lesson` | 要点卡片 + 当日全部题目（按启用的题型插件渲染）+ 解析 | 至少一个题型插件 |
| `page-review` | `review` | 错题册：未掌握题、重做入口、掌握状态、作废题过滤 | 无 |
| `page-progress` | `progress` | 完成讲次、正确率、作答次数、分讲进度条 | 无 |
| `page-notes` | `notes` | 笔记与简述答案汇总、导师回信展示 | `feature-mentor` 可选 |
| `page-about` | `about` | 课程来源、核实日期、译名订正、编排说明、版权声明 | 无 |
| `page-playground` | `playground` | 独立编程实验室；由 `q-code` 一并贡献时可省略单独插件 | `q-code` |

`page-index` / `page-lesson` / `page-about` 属于基础页面，`init_course_site.py` 在 `pages` 省略时自动补齐。

## 功能插件（`feature`）

| id | 钩子 | 作用 |
| --- | --- | --- |
| `feature-scope-lock` | `question:filter` | 依据 `concepts` 首次出现日过滤题目，隐藏未解锁概念；提供「这题没学过？」反馈入口 |
| `feature-mentor` | `state:loaded`、`after:submit`、`day:complete` | 维护 `HANDOFF.md` / `teaching-log.md` / `drafts.md` / `mentor-replies.json` 的读写约定；把写到一半的输入镜像给导师 |
| `feature-autosave` | `before:render` | 顶栏保存状态指示、离线暂存提示、关闭前强制同步（默认内置于内核，插件用于替换策略） |
| `feature-theme` | `before:render` | 主题切换；只替换 CSS 变量，不改插件代码 |

钩子返回值语义：

| 钩子 | 参数 | 返回值 |
| --- | --- | --- |
| `question:filter` | `(q, day)` | `true` 显示，`false` 当日隐藏 |
| `state:loaded` | `(state)` | 忽略 |
| `after:submit` | `(q, result)` | 忽略 |
| `day:complete` | `(n)` | 忽略 |
| `before:render` | `(route, ctx)` | 忽略 |

多个插件注册同一钩子时按加载顺序依次调用；`question:filter` 采用「全部通过才显示」的与逻辑。

## 两站对照

| 能力 | Python 私塾（8765） | MIT 6.00（8766） | 通用插件 |
| --- | --- | --- | --- |
| 课程编排 | 112 天 / 廖雪峰教程 | 24 讲 / 公开课 | `course.json` |
| 每日题量 | 5 选择 + 3 编程 | 10 单选 + 5 判断 + 5 多选 + 1 简述 | `site.json.quota` |
| 网页编程 | Pyodide + stdout 判题 | 不设编程题 | `q-code`（可关） |
| 超纲保护 | `unlockDay` / `TAG_DAY` | `concepts` 首次出现日 | `feature-scope-lock` |
| 笔记 | `notes/*.md` + Obsidian | 简述答案汇总 | `page-notes` |
| 导师 | `drafts.md` / 回信 / 复盘 | `HANDOFF` / `teaching-log` | `feature-mentor` |
| 错题 | 错题册 + 作废标记 | 错题册 + 重做 | `page-review` |
| 目录 / 进度 | 112 天目录 | 24 讲目录 | `page-catalog` / `page-progress` |
| 视觉 | 较早版本配色 | **温和配色（默认）** | `assets/skeleton/core/theme.css` |

## 新增插件的验收点

1. `plugins.json` 有元数据且 `entry` 文件存在。
2. `client.js` 只通过 `Site.register()` 注入，不直接访问 `localStorage` 或 `fetch`。
3. 需要的 `site.json` 字段已登记在 `data-contracts.md`。
4. 关闭该插件后 `verify_site.py` 仍全过（不能有隐藏依赖）。
5. 插件样式使用 `theme.css` 的变量，不写死颜色。
