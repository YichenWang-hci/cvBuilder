# Agent 指令 — 工作 / 实习经历口述录入

输入：用户用**任意语言**描述一段**实习或全职/兼职工作**经历（自由叙述）。  
输出：一条符合 `knowledge/experiences/*.yaml` 结构的记录（**de + en 双语**）。

## 与「项目」的区别

| | 项目 `projects/` | 工作/实习 `experiences/` |
|---|------------------|---------------------------|
| 场景 | 课程、个人、研究项目 | 公司、机构实习或工作 |
| 必有 | `title` | **`company`**（公司官方名） |
| 必有 | `role` | **`role`**（职位） |
| kind | — | `internship` 或 `work` |

输出格式与项目类似（bullets、keywords…），但 **company 必填**（用户未说则留空并在 report 标 TODO）。

## 提取字段

- `id`：slug，如 `acme-xr-intern`、`google-swe-work`
- `kind`：`internship`（实习/Praktikum/Werkstudent）或 `work`（全职/兼职工作）
- `company`：公司/机构官方名称（语言无关，如 `Siemens AG`、`2Sync GmbH`）
- `title`：可选副标题 `{ de, en }`（部门、产品线，不是职位）
- `role`：职位 `{ de, en }`（如 XR Development Intern / XR-Praktikantin）
- `period`：德式日期（见 DATA_FORMAT.md）
- `type`：`{ de: Praktikum, en: Internship }` 等
- `location`：可选，城市或 remote
- `tech_stack`, `keywords`, `target_roles`, `bullets`（最多 3 条）, `story_hooks`

## 硬性规则

1. **禁止编造**未提及的公司、职责、工具、成果
2. **company** 必须从叙述中提取；没有则 `""` + TODO
3. bullets：动词 + 动作 + 工具 + 结果；最多 3 条
4. 双语：role、type、bullets、title、story_hooks 需 de + en

## 输出 JSON

```json
{
  "experience": {
    "id": "slug",
    "kind": "internship",
    "company": "Company Name",
    "title": { "de": "", "en": "" },
    "role": { "de": "", "en": "" },
    "period": "",
    "type": { "de": "", "en": "" },
    "location": "",
    "tech_stack": [],
    "keywords": [],
    "target_roles": [],
    "bullets": [],
    "links": { "github": null, "demo": null, "paper": null },
    "story_hooks": { "problem": { "de": "", "en": "" }, ... }
  },
  "intake_report": "markdown"
}
```

只返回一个 JSON 对象，无 markdown 围栏。
