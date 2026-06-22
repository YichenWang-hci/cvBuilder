# Agent 生成指令 — 8 段简历 · 双语资料库

输入：JD + `knowledge/` 全部资料。  
输出：`applications/{company-role}/resume.json` + `cover_letter.md` + `match_report.md`

## ⛔ 单次生成 = 单语言（硬性）

**每一次生成任务，只产出一种语言的简历。** `meta.output_language` 必须是 `de` 或 `en` 之一。

| 允许 | 禁止 |
|------|------|
| 整份 resume.json 全部德文 | 同一份简历里德英混排 |
| 整份 resume.json 全部英文 | 同一字段同时输出 de 和 en |
| 德语 JD → 只取资料库 `.de` | 把 `{ de, en }` 对象原样写入 resume.json |
| 英语 JD → 只取资料库 `.en` | 一次生成里输出两份简历（德+英） |

需要德文版和英文版 → **分别运行两次生成**，输出到不同目录，例如：
- `applications/acme-hci-intern-de/`
- `applications/acme-hci-intern-en/`

### 输出前自检（必须全部通过）

- [ ] `meta.output_language` 为 `de` 或 `en`（不是 bilingual）
- [ ] §2–§4、§6–§7 所有 `value` / `text` / `name` / `degree` 均为**纯字符串**，不是 `{ de, en }` 对象
- [ ] 随机抽查 3 个字段：不含另一种语言的句子
- [ ] §8 语言块的 `name`、`level` 也使用**同一** output_language 版本
- [ ] `cover_letter.md` 语言与 `output_language` 一致

## 语言规则

1. **资料库**：存储 `{ de, en }` 双语（见各 yaml）— 仅作源数据，不直接输出
2. **检测 JD 语言**：德语 JD → `output_language: de`；英语 JD → `output_language: en`
3. **取值**：从资料库只读取与 `output_language` 匹配的那一侧，写入 resume.json 的字符串字段
4. **缺失翻译**：若该语言侧为空，在 `match_report.md` 标注 TODO，**跳过该字段或中止该条**，不得现场翻译或编造

### 各 § 双语取值

| § | 固定/可变 | de/en 来源 |
|---|----------|------------|
| 1 姓名 | 固定 | 语言无关，`name` 原样 |
| 2 自我描述 | 可变 | `summaries[].text.de` 或 `.en` |
| 3 学习经历 | 可变 | `degree.de` 或 `.en`；`school` / `period` 通常不变 |
| 4 项目/工作/实习 | 可变 | experiences：`company`+可选`title`→输出`title`；`role`、`bullets[].text`；projects：同前 |
| 5 联系方式 | 固定 | 语言无关 |
| 6 个人能力 | 可变 | `abilities[].name.de` 或 `.en` |
| 7 软件能力 | 可变 | `software[].name.de` 或 `.en` |
| 8 语言能力 | 固定 | `languages[].name.de/.en` 与 `level.de/.en` 按 output_language 选取 |

## 简历 8 段规则

| § | 区块 | 可变？ | 数据源 |
|---|------|--------|--------|
| 1 | 姓名 | **固定** | `profile.yaml` → `name` |
| 2 | 自我描述 | **可变** | `profile.yaml` → `summaries` |
| 3 | 学习经历 | **可变** | `profile.yaml` → `education` |
| 4 | 项目经历 | **可变** | `knowledge/projects/*.yaml` **+** `knowledge/experiences/*.yaml` |
| 5 | 联系方式 | **固定** | `profile.yaml` → `contact` |
| 6 | 个人能力 | **可变** | `abilities.yaml` |
| 7 | 软件能力 | **可变** | `software.yaml` |
| 8 | 语言能力 | **固定** | `profile.yaml` → `languages`（按 output_language 选 de/en 展示文案） |

### 可变字段补充

- §4 工作/实习：`experiences` 条目的 `title` 字段输出 **company**（若有 subtitle 可拼成 `Company — Subtitle`）；`role` 为职位
- §3：`period` 为空或不完整 → **跳过该条**（不编造），在 `match_report` 注明，**不中断生成**
- 日期展示：资料库 `period` 已为德式（见 `templates/DATA_FORMAT.md`），生成时原样复制，不改成 ISO
- §6 / §7：按 JD 选 subset + rank；只选有 evidence 的项（除非 report 说明例外）
- §2：实习向选 `context` 含 `internship` 的 summary

## 其他硬性规则

1. 遵守 `knowledge/WRITING_RULES.md`
2. 禁止编造
3. **§4 最多 3 段**（工作/实习 + 项目合计），每段最多 3 bullets；**优先选与 JD 最相关的**（含 `experiences` 中 internship/work）
4. 动机信 250–350 词，语言 = `output_language`
5. 自检：替换公司名后仍通用 → 重写

## 输出 schema

使用 `templates/resume-schema.json`，设置 `meta.output_language` 为 `de` 或 `en`。

## match_report.md 必含

- 检测到的 JD 语言与 `output_language`
- 缺失 de/en 翻译的字段列表
- §2–§7 选取与排序理由
