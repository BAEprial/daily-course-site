# 视觉规范：温和主题（默认）

默认主题取自 `mit-600-study/assets/app.css`：米白底、低饱和蓝主色、柔和的成功与错误反馈色。本 Skill 将其作为所有新站的默认主题，颜色统一收敛为 CSS 变量。

## 1. 设计令牌

```css
:root {
  --bg: #fafaf8;
  --surface: #ffffff;
  --line: #e4e2dc;
  --line-strong: #d2cfc6;
  --text: #24242a;
  --muted: #66666c;
  --hint: #8b8a84;
  --accent: #185fa5;
  --accent-soft: #eef4fb;
  --ok: #1d7a55;
  --ok-soft: #eaf5ef;
  --bad: #a4342f;
  --bad-soft: #fbeceb;
  --radius: 8px;
}
```

| 令牌 | 用途 |
| --- | --- |
| `--bg` / `--surface` | 页面底色 / 卡片与顶栏底色 |
| `--line` / `--line-strong` | 分隔线 / 输入框与按钮描边 |
| `--text` / `--muted` / `--hint` | 正文 / 次要说明 / 时间戳与标签 |
| `--accent` / `--accent-soft` | 主操作、选中态、链接 / 强调卡片底色 |
| `--ok` + `--ok-soft` | 答对、已掌握、已完成 |
| `--bad` + `--bad-soft` | 答错、保存失败 |
| `--radius` | 统一圆角，卡片 8px、按钮与选项 6px |

反馈色只用于状态，不用作大面积背景；错误态不使用高饱和纯红，避免压迫感。

## 2. 版式

- 字体：`system-ui, -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif`；正文 15px，行高 1.75。
- 内容区最大宽度 960px，居中；顶栏与页脚同宽。
- 标题层级：h1 24px / h2 18px / h3 15px，字重 600，不使用额外装饰。
- 卡片：白底、1px 边框、8px 圆角、20px 内边距，卡片间距 16px。
- 表格表头使用 `#f6f5f2` 浅底，不使用斑马纹。
- 题目卡片与选项使用同一套描边，选中 / 正确 / 错误只改边框与底色，不改字号。
- 640px 以下收窄内边距、减小标题字号，导航允许换行。

## 3. 页面骨架

每页固定三段：顶栏（品牌 + 导航 + 保存状态指示）、`<main class="wrap" id="app">`、页脚（课程来源与版权）。页面差异全部由插件的 `render` 填充，骨架不因课程变化。

保存状态指示用 7px 圆点：`--ok` 已保存、`#c08a20` 保存中、`--bad` 离线或失败；文字写明「已自动保存 HH:MM:SS」或「离线暂存 · 等待服务」。

## 4. 替换主题

主题是**数据而非代码**：

1. 复制 `assets/skeleton/core/theme.css` 为 `assets/skeleton/themes/<new-id>.css`，只改 `:root` 里的变量值。
2. 在 `site.json` 设置 `"theme": "<new-id>"`。
3. 重跑装配；`init_course_site.py` 会用指定主题覆盖 `assets/app.css` 的变量段。

禁止在插件 `client.js` 里写死颜色值；需要强调时只使用 `var(--accent)` 等变量。这样换主题不需要改任何插件。

## 5. 与 IDE 主题的关系

生成的是独立网页，默认使用浅色温和主题。若用户要求深色，另建一套深色令牌（深色底 + 浅色文字），保持同一组变量名，避免插件里出现条件判断。
