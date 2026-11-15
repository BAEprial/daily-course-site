# 数据契约

所有 JSON 使用 UTF-8。生成物 `assets/data/*.js` 只是 `window.COURSE = <json>;` 与 `window.QB = <json>;` 的包装，不手工编辑。

## 1. `site.json`（装配清单）

```json
{
  "name": "计算机科学及编程导论",
  "shortName": "CS 6.00",
  "port": 8766,
  "theme": "warm",
  "dailyMinutes": 30,
  "pages": ["index", "catalog", "lesson", "review", "progress", "notes", "about"],
  "plugins": ["q-single", "q-judge", "q-multi", "q-brief", "page-catalog", "page-review", "page-progress", "page-notes", "feature-mentor", "feature-scope-lock"],
  "quota": { "single": 10, "judge": 5, "multi": 5, "brief": 1 },
  "plan": [
    { "phase": "要点阅读", "minutes": 5 },
    { "phase": "单项选择", "minutes": 6 },
    { "phase": "判断与多选", "minutes": 10 },
    { "phase": "简述与复盘", "minutes": 9 }
  ],
  "source": {
    "name": "MIT 6.00 Fall 2008 / 网易公开课",
    "url": "https://open.163.com/...",
    "verifiedAt": "2026-11-15",
    "copyright": "视频与课程名称版权归原作者所有"
  }
}
```

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `name` / `shortName` | 是 | 站点标题与顶栏短名 |
| `port` | 是 | 本地端口，不同站点必须不同（已用：8765、8766） |
| `theme` | 是 | 主题 id，默认 `warm` |
| `dailyMinutes` / `plan` | 是 | 每日时长与环节分配，展示在首页与课程说明页 |
| `plugins` | 是 | 启用的插件 id 列表，顺序即加载顺序（依赖由装配脚本拓扑排序） |
| `pages` | 否 | 生成的页面；省略时由 `page` 类插件自动推导，并补 `index` / `lesson` / `about` |
| `quota` | 是 | 每种 `q.type` 的每日题量，`verify_site.py` 按此校验 |
| `source` | 是 | 课程来源与核实日期；`verifiedAt` 必须是实际核实日期，不填推测值 |

需要编程题时追加：

```json
"pyodide": { "cdn": "https://cdn.jsdelivr.net/pyodide/v314.0.8/full/", "version": "314.0.8", "verifiedAt": "2026-11-14" }
```

版本号属易变事实，启用前须联网核实并更新日期。

## 2. `data/course.json`

```json
{
  "meta": { "name": "…", "nameEn": "…", "lectures": 24, "dailyMinutes": 30, "description": "…" },
  "lectures": [
    {
      "id": "d01",
      "day": 1,
      "zh": "课程目标，数据类型，运算，变量",
      "en": "Introduction and Goals; Data Types, Operators, and Variables",
      "url": "https://…",
      "concepts": ["计算思维", "算法", "解释器", "变量与赋值"],
      "points": ["本讲面向…", "算法是一组…"],
      "note": ""
    }
  ],
  "termNotes": [
    { "day": 6, "wrong": "数组", "right": "列表（list）", "why": "英文原题为 list，不是 array" }
  ]
}
```

- `lectures[].concepts` 是**该讲首次引入的概念清单**，超纲校验的依据。
- 概念首次出现日 = 其所在讲次的 `day`；题目 `concept` 必须等于某个已登记概念，或登记在 `extraConcepts` 中。
- `points` 是要点卡片，使用结构完整的陈述句。
- `termNotes` 记录译名订正；当课程原标题存在误译时必填，出题按订正后的概念边界。
- 可选 `extraConcepts`: `{ "课程目标": 1, "课程简介": 1 }`，用于不属于任何讲次技术概念的通用知识点。

## 3. `data/questions.json`

```json
{
  "questions": [
    {
      "id": "d01-s01",
      "day": 1,
      "type": "single",
      "stem": "本课程面向的主要学习者群体是哪一类？",
      "options": ["…", "…", "…", "…"],
      "answer": [1],
      "explain": "课程介绍明确说明…",
      "concept": "课程简介"
    },
    {
      "id": "d01-b01",
      "day": 1,
      "type": "brief",
      "stem": "用自己的话说明算法与程序的区别。",
      "options": [],
      "answer": [],
      "explain": "",
      "concept": "算法",
      "keypoints": ["…", "…"],
      "guide": "用两到三句话作答，写完后对照参考要点自评。"
    }
  ]
}
```

| 字段 | 说明 |
| --- | --- |
| `id` | 全局唯一，建议 `<dayId>-<type首字母><序号>` |
| `day` | 所属讲次 |
| `type` | 必须对应一个已启用的 `question-type` 插件的 `handles` |
| `stem` / `options` | 题干与选项；判断题固定 `["正确","错误"]` |
| `answer` | 客观题为正确选项下标数组（从 0 开始）；简述题与编程题为 `[]`，编程题由 `q-code` 把 stdout 字符串作为作答值提交，判题依据写在 `judge.expected` |
| `explain` | 解析，完整陈述句 |
| `concept` | 知识点，用于超纲校验与错题归类 |
| `keypoints` / `guide` | 简述题参考要点与作答说明 |
| `judge` | 编程题专用判题配置：`{"mode":"stdout","expected":"Hello, world!","looseSpace":true}` 或 `{"mode":"compare","ref":"…","cases":[[…]]}` |

**判题口径**：看屏幕输出（stdout），不看代码文本。文字照抄类题忽略空格差异（`looseSpace`），单双引号等价；计算结果与容器输出严格比对。编程题判题配置由 `q-code` 插件解释，内核不参与。

## 4. `records/state.json`（唯一事实源）

```json
{
  "version": 1,
  "updatedAt": "2026-11-15T13:27:10Z",
  "progress": {
    "d01": { "answers": { "d01-s01": [1] }, "correct": { "d01-s01": true }, "done": false, "completedAt": null }
  },
  "attempts": [
    { "id": "a<timestamp>", "ts": "…", "day": 1, "qid": "d01-s01", "type": "single", "answer": [1], "correct": true }
  ],
  "wrongBook": [
    { "qid": "d01-s02", "day": 1, "stem": "…", "wrongCount": 1, "lastWrong": "…", "mastered": false, "retired": false, "note": "" }
  ],
  "briefs": { "d01": { "text": "…", "selfChecked": false } },
  "drafts": { "d01-brief": "写到一半的内容" },
  "notes": {},
  "settings": {}
}
```

- `attempts[].id` 是合并键，必须全局唯一且稳定（时间戳 + 随机后缀）。
- `wrongBook[].retired: true` 表示超纲作废题，不计入正确率，也不再出现在错题册。
- 服务端按 `architecture.md` §8 的规则合并；前端不直接写文件。
- 其他 md（笔记、错题册镜像）都是派生文件，可能过期或被覆盖，**不得当作事实源**。

## 5. `plugins.json`（插件元数据）

见 `architecture.md` §6.4。字段：`id`、`kind`、`handles`、`label`、`entry`、`navLabel`、`requires`、`defaultOn`、`summary`。

- 骨架清单：`assets/skeleton/plugins.json`，`entry` 相对骨架根目录，例如 `plugins/q-single/client.js`。
- 站点本地清单：目标站根目录 `plugins.json`，格式相同（数组），`entry` 相对站点根目录。装配时与骨架清单按 id 合并，本地条目覆盖同名骨架条目；插件实现文件也优先从站点目录读取。
- 合并结果写入 `tools/plugins.json`，供 `verify_site.py` 读取。

新增一个站点专属插件时，只需这两步中的本地文件，不必修改 Skill 骨架。

## 6. `records/HANDOFF.md`（教学上下文，非事实源）

固定章节：防幻觉规则、学员画像与教学约定、当前状态快照（注明读取时间）、已讲概念与已定口径、错题档案、未结问题、下一讲计划、文件权威层级、维护协议。

只放一份「当前进度」；被推翻的结论标注「已收回」而不删除；每次练习后追加 `teaching-log.md` 并更新交接卡。骨架模板见 `assets/skeleton/records/HANDOFF.template.md`。
