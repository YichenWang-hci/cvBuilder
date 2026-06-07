# Agent 指令 — 资料库固定信息录入（P0）

输入：用户用**任意语言**提供的个人固定信息（问答或自由叙述）。  
输出：`knowledge/profile.yaml` 中的固定区块 + 一条入门 `summaries` 草稿。

## 你的任务

把用户输入**结构化**为 profile 数据，并生成 **德语 (de)** 和 **英语 (en)** 双语字段。

## 硬性规则

1. **禁止编造**：用户没说的学校、日期、语言等级、联系方式不得写入
2. **缺失不报错**：无法推断的字段写 `""`，在 `intake_report` 的 TODO 列出；**仍输出完整 profile**
3. **翻译**：`degree`、`languages[].name/level`、`application_context.note`、`summaries[].text` 必须同时有 `de` 和 `en`（缺一侧则该侧 `""` + TODO）
4. **语言无关字段**：`name`、`school` 原样保留；`contact.phone` 规范为 **DIN 5008** 国际格式（`+49 152 06820364`，见 `templates/DATA_FORMAT.md` §1.1）
5. **日期（德式）**：所有 `period`、`earliest_start` 遵守 `templates/DATA_FORMAT.md` — **TT.MM.JJJJ** 或 **MM.JJJJ** 或 **Monat JJJJ**，范围用 ` - `，进行中用 `heute`；把 ISO/美式日期转换为德式
6. **教育 `id`**：根据学校生成 slug，如 `edu-tum`、`edu-wuerzburg`
7. **一条入门 summary**：根据教育/目标生成 `summaries[0]`，`id` 为 `default-intern`，`context` 含 `internship`；只写用户输入中能支持的事实，1–2 句

## 输出 schema

```json
{
  "profile": {
    "name": "string",
    "contact": {
      "email": "string",
      "phone": "string",
      "address": "string"
    },
    "languages": [
      {
        "name": { "de": "string", "en": "string" },
        "level": { "de": "string", "en": "string" }
      }
    ],
    "summaries": [
      {
        "id": "default-intern",
        "context": ["internship"],
        "text": { "de": "string", "en": "string" }
      }
    ],
    "education": [
      {
        "id": "edu-slug",
        "school": "string",
        "degree": { "de": "string", "en": "string" },
        "period": "string",
        "relevance": ["keyword"]
      }
    ],
    "application_context": {
      "goal": "full-time-intern",
      "earliest_start": "MM.JJJJ (e.g. 08.2026) or empty string",
      "duration": "string or empty",
      "days_per_week": 5,
      "note": { "de": "string", "en": "string" }
    }
  },
  "intake_report": "markdown — detected input language, parsed fields, TODOs, assumptions"
}
```

## 常见语言等级映射（展示文案）

| 用户说法 | de | en |
|---------|----|----|
| 母语/Native | Muttersprache | Native |
| C1 | C1 | C1 |
| B2 | B2 | B2 |
| 流利/Fluent | Fließend | Fluent |

## 禁止

- 输出 markdown 代码围栏
- 在 JSON 外附加说明文字
- 编造项目经历（项目由 P1 `add_experience.py` 处理，本次不输出 projects）
