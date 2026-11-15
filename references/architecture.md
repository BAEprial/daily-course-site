# 框架架构与插件契约

## 1. 设计目标

同一套内核要能承载「112 天 Python 教程 + 5 选择 3 编程」和「24 讲计算机科学导论 + 10 单选 5 判断 5 多选 1 简述」这两种差异极大的站点，也能承载未来的英语、数学、考纲类课程。差异全部落在插件与数据上，内核不因课程变化而改写。

由此确定三条边界：

1. 内核不认识任何题型、任何页面名称、任何学科术语。
2. 插件不直接读写 `records/state.json`，一律通过内核 API。
3. 课程内容、题目、站点装配信息分别放在三份数据文件里，生成物不手工编辑。

## 2. 三层结构

```
装配层  site.json ──> init_course_site.py ──> 静态站点目录
                         │ 复制 core/
                         │ 按 plugins 列表复制 plugins/<id>/
                         │ 生成 assets/data/*.js、页面 HTML、server.py、start.bat
                         ▼
内核层  Site 单例（core.js）  ──────────────────  稳定，不随课程变化
        ├ 状态：加载、规范化、本地暂存、合并提交
        ├ 自动保存：250ms 防抖 + 隐藏/关闭强制同步
        ├ 路由：按 body[data-page] 调用已注册页面插件
        ├ 每日编排：lectureOf(n) / questionsOf(n) / progressOf(n)
        ├ 作答：submit() 统一记 attempts / wrongBook / progress
        └ 事件总线：on / emit，供 feature 插件介入
                         ▲ 注册
插件层  question-type │ page │ feature
数据层  data/course.json  data/questions.json  records/state.json
```

## 3. 数据流

```
data/course.json ─┐
                  ├─ build ─> assets/data/course.js ─> Site.course
data/questions.json ┘        assets/data/questions.js ─> Site.questions

用户作答 ─> 题型插件 ctx.submit(answer)
        ─> Site.submit() ─> grade() ─> state.attempts / wrongBook / progress
        ─> Site.save() ─> POST /api/state ─> 服务端合并写入 ─> records/state.json
                                        ├─ records/state.backup.json
                                        └─ records/drafts.md（导师读）
```

导师不直接读浏览器：只读 `records/state.json`（机器事实）、`records/HANDOFF.md`（教学上下文）、`records/teaching-log.md`（过程历史）、`records/drafts.md`（未点保存的输入）。回信写 `records/mentor-replies.json`，由页面插件展示。

## 4. 目录规范

```
<site>/
├── site.json                 装配清单（唯一开关）
├── data/
│   ├── course.json           课程与讲次
│   └── questions.json        题库
├── assets/
│   ├── core/                 内核（复制自骨架，不手改）
│   │   ├── core.js
│   │   └── theme.css
│   ├── plugins/<id>/         启用的插件（每个一个目录）
│   ├── data/course.js        生成物
│   ├── data/questions.js     生成物
│   ├── app.css               生成物：theme + 插件样式
│   └── site-config.js        生成物：window.SITE_CONFIG
├── records/
│   ├── state.json            唯一事实源
│   ├── state.backup.json
│   ├── drafts.md
│   ├── HANDOFF.md
│   └── teaching-log.md
├── notes/                    笔记（可选）
├── index.html / catalog.html / lesson.html / ...   生成物
├── server.py
├── start.bat
├── tools/verify.py           通用自检副本
└── README.md
```

生成物（页面、`assets/data/*.js`、`app.css`）一律由装配脚本重建，修改内容要去改 `data/` 或插件。

## 5. 内核 API（`core.js` 暴露 `window.Site`）

| 成员 | 说明 |
| --- | --- |
| `Site.config` / `course` / `questions` | 装配配置、课程数据、题库 |
| `Site.state` | 规范化后的状态对象 |
| `Site.online` | 是否连上本地服务 |
| `Site.register(kind, name, impl)` | 插件注册入口，`kind` 为 `question-type` / `page` / `feature` |
| `Site.on(event, fn)` / `Site.emit(event, payload)` | 事件总线 |
| `Site.save(immediate)` / `Site.flush()` | 防抖保存 / 关闭前强制同步 |
| `Site.day(n)` | 返回 `{id, lecture, questions, progress}` |
| `Site.currentDay()` | 当前讲次：优先 URL 的 `?day=N`，否则取第一个未完成讲次 |
| `Site.questionsOf(n)` / `Site.progressOf(n)` | 取当日题目（经过 `question:filter` 钩子）/ 进度 |
| `Site.renderQuestion(q)` | 按 `q.type` 调用已注册题型插件，返回可挂载的节点 |
| `Site.submit(q, answer)` | 调用题型插件 grade，记录作答、错题、进度并保存 |
| `Site.setDraft(key, text)` | 写草稿（自动落盘、镜像到 `drafts.md`） |
| `Site.completeDay(n)` | 标记当日完成 |
| `Site.esc(s)` / `Site.h(tag, attrs, children)` | 转义与 DOM 构造助手 |
| `Site.pill(text, status)` | 更新顶栏保存状态 |

状态的规范化字段见 `data-contracts.md`。

## 6. 插件契约

### 6.1 `question-type`

```js
Site.register('question-type', 'single', {
  label: '单项选择',
  autoGrade: true,
  grade: function (q, answer) { return { correct: true }; },  // 无判分则返回 null
  render: function (q, ctx) { return HTMLElement; }
});
```

`ctx` 提供 `q`、`day`、`answer`（已存答案）、`locked`（是否已作答被锁定）、`submit(answer)`、`setDraft(text)`、`h`、`esc`。
`render` 只负责界面与收集答案，**不写状态**；点击提交统一调用 `ctx.submit()`，由内核判分、记错题、保存。
`grade` 返回 `{correct: boolean, detail?: string}`；简述题返回 `null` 表示不自动判分。

### 6.2 `page`

```js
Site.register('page', 'catalog', {
  label: '课程目录',
  navLabel: '课程目录',
  render: function (ctx) { return HTMLElement; }
});
```

`route` 与插件 id 一致，装配脚本据此生成 `catalog.html` 与顶栏导航。`render` 返回挂在 `<main id="app">` 下的节点。

### 6.3 `feature`

```js
Site.register('feature', 'scope-lock', {
  init: function (ctx) {},
  hooks: {
    'question:filter': function (q, day) { return true; },  // false 表示该题当日不出现
    'state:loaded': function (state) {},
    'after:submit': function (q, result) {},
    'day:complete': function (n) {},
    'before:render': function (route, ctx) {}
  }
});
```

`feature` 用于横切能力：超纲锁、导师桥、主题切换、统计埋点。钩子返回值语义由钩子名决定，见 `plugin-catalog.md`。

### 6.4 插件元数据（`plugins.json` 单条）

```json
{
  "id": "q-single",
  "kind": "question-type",
  "handles": "single",
  "label": "单项选择",
  "entry": "plugins/q-single/client.js",
  "navLabel": "",
  "requires": [],
  "defaultOn": true,
  "summary": "四选一，选择后立即判定并显示解析"
}
```

`page` 类插件用 `id` 作为 `route`，并填写 `navLabel`；`feature` 类插件不填 `handles`。`requires` 用于声明依赖，装配脚本按拓扑顺序加载并在缺失时报错。

## 7. 新增插件步骤

**方式 A · 做成可复用插件（放进 Skill 骨架，所有站点可用）**

1. 在 `assets/skeleton/plugins/<new-id>/client.js` 写一个 `Site.register()` 调用。
2. 在 `assets/skeleton/plugins.json` 增加一条元数据。
3. 目标站 `site.json` 的 `plugins` 加入 `<new-id>`，重跑装配与自检。

**方式 B · 只给某一个站点用（放进站点目录，不污染全局）**

1. 在目标站 `plugins/<new-id>/client.js` 写注册调用。
2. 在目标站 `plugins.json` 增加一条元数据，`entry` 写 `plugins/<new-id>/client.js`。
3. 在 `site.json` 的 `plugins` 加入该 id，重跑装配与自检。

装配脚本优先读取站点本地实现，找不到才回退到骨架；本地元数据同名时覆盖骨架条目，因此也可以只覆盖某个插件的实现。合并后的清单写入 `tools/plugins.json` 供自检使用。

两种方式都要求：插件需要新数据字段时登记到 `data-contracts.md`，并同步增加 `verify_site.py` 的检查项。内核与服务端零改动。插件之间禁止互相直接引用；需要协作时通过 `Site.on/emit` 或钩子。

## 8. 服务端职责（稳定）

`core/server.py` 只做四件事：静态文件、`GET/POST /api/state`、`GET /api/health`、原子写入与备份。合并规则固定：

- `attempts` 按 `id` 合并，保留双方独有记录；
- `progress` 按 Day 合并，`done` 只升不降，`completedAt` 保留最早值；
- `wrongBook` 按 `qid` 合并，`wrongCount` 取较大值；
- `drafts` / `notes` 非空值优先，空白不覆盖已有内容；
- 每次写入前备份到 `state.backup.json`，并重建 `drafts.md`。

禁止「前端 POST 什么就覆盖什么」。换浏览器、旧标签页、离线暂存恢复都依赖这条规则。

## 9. 自检必须固化为脚本

人工检查会漏掉编码、超纲、答案下标、页面引用这类问题。`verify_site.py` 至少覆盖：插件完整性、题型覆盖、每日题量、答案合法性、概念首次出现日、页面引用存在、`start.bat` 为 CRLF 且纯 ASCII、服务端临时副本冒烟。新增插件时同步新增检查项。
