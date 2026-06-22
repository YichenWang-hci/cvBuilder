# Agent 指令 — 项目经历口述录入

输入：用户用**任意语言**描述一段项目/实习/工作经历（自由叙述）。  
输出：一条符合 `knowledge/projects/*.yaml` 结构的项目记录（**de + en 双语**）。

## 任务

从叙述中**提取**（禁止编造用户未提及的事实）：

- `id`：slug，小写连字符，如 `vr-3d-ui`、`ml-gesture`
- `title`、`role`、`type`：各 `{ de, en }`
- `period`：德式日期，见 `templates/DATA_FORMAT.md`（`MM.JJJJ` 或 `TT.MM.JJJJ`，` - `，进行中用 `heute`）
- `tech_stack`：工具/技术列表
- `keywords`：从叙述提炼的匹配 JD 用词（英文小写为主）
- `target_roles`：适合的实习岗位类型，如 `hci intern`, `vr intern`
- `bullets`：最多 **3** 条，每条 `{ id, text: {de,en}, tags, metric }`
  - 格式：动词 + 做了什么 + 用什么 + 结果
  - `tags`：从 bullet 提炼的关键词
- `story_hooks`（可选）：`problem`, `constraint`, `decision`, `outcome`, `lesson` 各 `{ de, en }`，仅当叙述有足够信息时填写，否则空字符串

## 硬性规则

1. **禁止编造**：未提到的技术、数字、公司、结果不得写入
2. **缺失**：无法推断的字段用 `""` 或 `[]`，在 `intake_report` 标 TODO
3. **双语**：`title`、`role`、`type`、`bullets[].text`、`story_hooks` 必须 de + en；可翻译用户未提供的一侧，但不得添加新事实
4. **keywords**：至少 3 个，从用户原话或明确技术栈提取
5. **type** 推断：`Universitätsprojekt` / `Praktikum` / `Projekt` 及英文对应

## 输出 JSON

```json
{
  "project": {
    "id": "slug",
    "title": { "de": "", "en": "" },
    "role": { "de": "", "en": "" },
    "period": "",
    "type": { "de": "", "en": "" },
    "tech_stack": [],
    "keywords": [],
    "target_roles": [],
    "bullets": [
      { "id": "b1", "text": { "de": "", "en": "" }, "tags": [], "metric": null }
    ],
    "links": { "github": null, "demo": null, "paper": null },
    "story_hooks": {
      "problem": { "de": "", "en": "" },
      "constraint": { "de": "", "en": "" },
      "decision": { "de": "", "en": "" },
      "outcome": { "de": "", "en": "" },
      "lesson": { "de": "", "en": "" }
    }
  },
  "intake_report": "markdown — 检测语言、提取的关键词列表、TODO、假设"
}
```

只返回一个 JSON 对象，无 markdown 围栏，无 JSON 外文字。
