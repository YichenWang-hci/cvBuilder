# cvBuilder

Local-first resume builder — maintain a personal knowledge base on your machine, paste a job description (JD), and generate a tailored resume + cover letter. Optional Figma fill if you bring your own template.

本地优先的简历生成工具 — 在本机维护个人资料库，粘贴招聘启事（JD），生成定制简历与动机信。可自备 Figma 模板做可选的一键填充。

- Data stays in `knowledge/` (gitignored). Terminal CLI or local web UI at `http://127.0.0.1:5050`. Resume output in **German** or **English** (one language per run). **Projects** for students; **Work & Internships** for job experience — both feed resume §4.
- 数据保存在本机 `knowledge/`（不会提交到 git）。支持终端 CLI 或本地网页 `http://127.0.0.1:5050`。每次生成一种语言（**德语**或**英语**）。学生填 **Projects（项目）**；有实习/工作经历填 **Work & Internships（工作/实习）** — 共同组成简历第 4 段。

> **Figma template not included · 不提供 Figma 简历模板**  
> This repo does **not** ship a ready-made Figma resume file. You can still use `resume.json`, `resume.txt`, and `cover_letter.md`. Figma is optional: create your own template, name layers as documented, import the included plugin, paste `figma-fill-payload.json`.  
> 本仓库**不包含**现成的 Figma 简历设计文件。你仍可完整使用生成能力。Figma 为可选：自备模板、按文档命名文字图层、导入自带插件、粘贴 `figma-fill-payload.json` 即可填充。

---

## Table of contents · 目录

- [Requirements · 环境要求](#requirements--环境要求)
- [Quick start · 快速开始（首次）](#quick-start--快速开始首次)
- [Every new terminal session · 每次新开终端](#every-new-terminal-session--每次新开终端)
- [Configure LLM · 配置 LLM](#configure-llm--配置-llm)
- [Step 1 — Knowledge base · 步骤 1 — 资料库](#step-1--knowledge-base--步骤-1--资料库)
- [Step 2 — Profile & experience · 步骤 2 — 填写经历](#step-2--profile--experience--步骤-2--填写经历)
- [Step 3 — Generate resume · 步骤 3 — 生成简历](#step-3--generate-resume--步骤-3--生成简历)
- [Local web UI · 本地网页](#local-web-ui--本地网页)
- [Knowledge layout · 资料库结构](#knowledge-layout--资料库结构)
- [Output files · 输出文件](#output-files--输出文件)
- [Optional Figma · 可选 Figma 流程](#optional-figma--可选-figma-流程)
- [CLI reference · 命令行参数](#cli-reference--命令行参数)
- [Troubleshooting · 常见问题](#troubleshooting--常见问题)
- [Privacy · 隐私与数据](#privacy--隐私与数据)
- [Project structure · 项目结构](#project-structure--项目结构)
- [Typical workflow · 典型流程](#typical-workflow--典型流程)

---

## Requirements · 环境要求

| Item | English | 中文 |
|------|---------|------|
| **Python** | 3.10+ (3.11 tested) | 3.10 及以上 |
| **OS** | macOS, Linux, Windows | macOS / Linux / Windows |
| **Git** | To clone the repo | 用于克隆仓库 |
| **LLM API** | Gemini (free), Ollama, or OpenAI | 见下方配置章节 |
| **Figma** | Optional — BYO template only | 可选 — 需自备模板 |

---

## Quick start · 快速开始（首次）

Run inside the folder you cloned — **do not** use a personal absolute path like `/Users/...`.

在**你 clone 下来的项目文件夹内**执行 — **不要**写个人绝对路径（如 `/Users/...`）。

```bash
# 1. Clone / 克隆
git clone https://github.com/YichenWang-hci/cvBuilder.git
cd cvBuilder

# 2. Virtual environment / 虚拟环境
python3 -m venv .venv

# 3. Activate / 激活
# macOS / Linux:
source .venv/bin/activate
# Windows (CMD):
# .venv\Scripts\activate.bat
# Windows (PowerShell):
# .venv\Scripts\Activate.ps1

# 4. Dependencies / 依赖
pip install -r requirements.txt

# 5. API keys / 配置密钥
cp .env.example .env
# Edit .env / 编辑 .env

# 6. Empty knowledge template / 初始化空资料库
python onboard.py --init

# 7. Profile intake / 录入固定信息（可用任意语言）
python onboard.py

# 8. Verify (no LLM call) / 检查资料库（不调用 LLM）
python generate.py --dry-run
```

Success → prompt shows `(.venv)` at the start.

成功时命令行前会出现 `(.venv)`。

---

## Every new terminal session · 每次新开终端

```bash
cd cvBuilder                    # your clone path / 你的 clone 目录
source .venv/bin/activate       # Windows: see above / Windows 见上
```

Then run `python manage.py`, `python generate.py`, etc.

之后可运行 `python manage.py`、`python generate.py` 等。

---

## Configure LLM · 配置 LLM

```bash
cp .env.example .env
```

### Option A — Gemini（推荐 / recommended, free tier）

1. Key: https://aistudio.google.com/apikey  
2. `.env`:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.5-flash-lite
```

No credit card for free tier (Google limits apply).

免费额度无需信用卡（受 Google 配额限制）。

### Option B — Ollama（本地免费 / local free）

```bash
ollama pull llama3.2
```

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
OLLAMA_HOST=http://localhost:11434
```

### Option C — OpenAI（付费 API / paid）

ChatGPT Plus does **not** include API billing.

ChatGPT Plus **不包含** API 费用。

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

---

## Step 1 — Knowledge base · 步骤 1 — 资料库

Creates local `knowledge/` from committed `knowledge.example/` (empty placeholders).

从仓库内的 `knowledge.example/` 复制到本机 `knowledge/`（空模板，不含个人数据）。

```bash
python onboard.py --init
```

| Flag | English | 中文 |
|------|---------|------|
| `--init` | Copy template → `knowledge/` | 复制模板到 `knowledge/` |
| `--force` | Overwrite existing `knowledge/` | 覆盖已有 `knowledge/` |

---

## Step 2 — Profile & experience · 步骤 2 — 填写经历

### Profile（CLI）

```bash
python onboard.py              # Interactive / 逐步问答
python onboard.py --paste        # Paste block / 一次性粘贴
python onboard.py --keep-summaries   # Keep summaries / 保留已有自我描述
```

**End paste input / 结束粘贴：** macOS/Linux **Ctrl+D** · Windows **Ctrl+Z** then Enter

### Projects & work（web UI recommended / 推荐网页）

| User | English | 中文 |
|------|---------|------|
| Student | **Projects** — coursework, research | **Projects（项目）** — 课程、个人、研究 |
| Employed / intern | **Work & Internships** | **Work & Internships（工作/实习）** |
| Both | §4 max 3 items; work first | 第 4 段最多 3 条，优先工作/实习 |

Web **narrative intake** — describe in any language → LLM drafts de/en YAML → you review.

网页 **口述录入** — 任意语言描述 → LLM 生成 de/en 双语 YAML → 确认后保存。

也可直接编辑 `knowledge/` 下 YAML 文件。

---

## Step 3 — Generate resume · 步骤 3 — 生成简历

```bash
python generate.py                          # Paste JD / 粘贴 JD
python generate.py --jd-file path/to/jd.txt
python generate.py --jd-file jd.txt --lang de   # Force German / 强制德语
python generate.py --jd-file jd.txt --lang en   # Force English / 强制英语
python generate.py --jd-file jd.txt --quiet      # Files only / 只写文件
```

After pasting JD in terminal, press **Ctrl+D** (macOS/Linux). Wait ~20–60 s.

终端粘贴 JD 后按 **Ctrl+D**，等待约 20–60 秒。

---

## Local web UI · 本地网页

```bash
cd cvBuilder
source .venv/bin/activate
python manage.py
```

Open **http://127.0.0.1:5050**

| Page | English | 中文 |
|------|---------|------|
| Profile | Name, contact, education, languages | 固定信息 |
| Work & Internships | `knowledge/experiences/*.yaml` | 工作 / 实习 |
| Projects | `knowledge/projects/*.yaml` | 项目 |
| Abilities / Software | Skills for JD matching | 能力 / 软件 |
| Figma Layers | Required layer names for your template | Figma 图层命名列表 |
| Generate Resume | Paste JD → `applications/` | 生成简历 |

Web and CLI share `knowledge/` and `.env`. Home page: **Get Started** or scroll down to enter the app; **View Templates** opens a video link when configured in `web/site.yaml` (`templates_video_url`) or `.env` (`TEMPLATES_VIDEO_URL`).

网页与终端共用 `knowledge/` 与 `.env`。首页 **Get Started** 或向下滑进入使用；**View Templates** 可在 `web/site.yaml` 或 `.env` 配置 YouTube 等链接后打开。

---

## Knowledge layout · 资料库结构

```
knowledge/                 # gitignored / 不提交
├── profile.yaml           # §1–§3, §5, §8
├── abilities.yaml         # §6
├── software.yaml          # §7
├── projects/              # §4 projects / 项目
├── experiences/           # §4 work & internships / 工作实习
├── WRITING_RULES.md
└── DATA_FORMAT.md         # DE dates, DIN 5008 phone / 德式日期与电话
```

Committed template: `knowledge.example/` · Format rules: `templates/DATA_FORMAT.md`

仓库模板：`knowledge.example/` · 格式说明：`templates/DATA_FORMAT.md`

---

## Output files · 输出文件

```
applications/20260601-153045-acme-intern/
├── jd.txt
├── resume.txt
├── resume.json
├── cover_letter.md
├── match_report.md
└── figma-fill-payload.json    # if --fill-figma / 勾选 Figma JSON
```

**Open latest (macOS)：**

```bash
open applications/$(ls -t applications | head -1)/resume.txt
```

Linux:

```bash
xdg-open applications/$(ls -t applications | head -1)/resume.txt
```

---

## Optional Figma · 可选 Figma 流程

**No Figma resume file in this repo.** To use fill:

**仓库不提供 Figma 简历文件。** 使用填充功能需：

1. Design your own resume in Figma / 在 Figma 中自备简历模板  
2. Name text layers per **Figma Layers** page or `templates/figma-template-map.yaml` / 文字图层名与网页 **Figma Layers** 或映射文件一致  
3. Import plugin: `figma-plugin/manifest.json` / 导入开发插件  
4. Generate with Figma JSON / 生成时导出 JSON:

```bash
python generate.py --jd-file jd.txt --fill-figma
python fill_figma.py applications/your-folder/resume.json
```

5. Plugin **cvBuilder Fill** → paste `figma-fill-payload.json` → **Fill resume** / 插件粘贴 JSON → **Fill resume**

Optional `.env`: `FIGMA_ACCESS_TOKEN`, `FIGMA_FILE_KEY`, `FIGMA_TEMPLATE_FRAME`

---

## CLI reference · 命令行参数

### `onboard.py`

| Flag | English | 中文 |
|------|---------|------|
| `--init` | Create `knowledge/` | 初始化资料库 |
| `--force` | Overwrite on init | 强制覆盖 |
| `--paste` | Single-block intake | 一次性粘贴 |
| `--keep-summaries` | Keep summaries | 保留 summaries |
| `--yes` / `-y` | Save without confirm | 跳过确认 |
| `--dry-run` | No LLM | 不调用 LLM |
| `--provider` | gemini \| ollama \| openai | 指定 LLM |

### `generate.py`

| Flag | English | 中文 |
|------|---------|------|
| `--jd-file` | JD file path | JD 文件路径 |
| `--lang de\|en` | Force language | 强制输出语言 |
| `--dry-run` | Load knowledge only | 仅加载资料库 |
| `--quiet` | No terminal print | 不打印到终端 |
| `--fill-figma` | Write Figma JSON | 导出 Figma JSON |
| `--copy-figma-clipboard` | Copy JSON (macOS) | 复制到剪贴板 |
| `--output-dir` | Custom folder | 自定义输出目录 |

### `manage.py`

Local web server at `127.0.0.1:5050`

启动本地网页服务

---

## Troubleshooting · 常见问题

| Problem | Fix |
|---------|-----|
| `command not found: python` | Use `python3` / 改用 `python3` |
| No `(.venv)` | `source .venv/bin/activate` from project root / 在项目根目录激活 |
| `knowledge/ not found` | `python onboard.py --init` |
| Pasted JD, no output | **Ctrl+D** after paste / 粘贴后 **Ctrl+D** |
| API key errors | Check `.env` in project root / 检查根目录 `.env` |
| `command not found: #` | Don't paste comment lines / 勿粘贴 `#` 注释行 |
| Wrong language | `--lang de` or `--lang en` / 使用 `--lang de` 或 `--lang en` |
| Figma fill fails | Layer names must match; BYO template / 图层名须完全一致；需自备模板 |
| Old hero image | Replace `web/design/webDesign.png`; restart `manage.py` / 替换首图后重启 `manage.py` |

---

## Privacy · 隐私与数据

| Local only | In git |
|------------|--------|
| `knowledge/` — personal data / 个人资料 | `knowledge.example/` — empty template / 空模板 |
| `applications/` — outputs / 生成结果 | Code, prompts, plugin / 代码与插件 |
| `.env` — API keys / 密钥 | `.env.example` |

Web UI listens on `127.0.0.1` only — no cvBuilder cloud upload.

网页仅绑定本机，不上传到任何 cvBuilder 服务器。

---

## Project structure · 项目结构

```
cvBuilder/
├── onboard.py              # Profile → profile.yaml
├── generate.py             # JD → resume + cover letter
├── fill_figma.py           # resume.json → Figma payload
├── manage.py               # Web UI / 网页
├── agent/                  # LLM prompts
├── web/                    # Flask app
├── knowledge.example/      # Committed template / 提交的空模板
├── figma-plugin/           # Dev plugin (BYO template) / 插件
├── figma_fill/
├── templates/
└── requirements.txt
```

---

## Typical workflow · 典型流程

```bash
cd cvBuilder
source .venv/bin/activate

python onboard.py --init
python onboard.py

python manage.py
# Browser: Projects / Work & Internships / Abilities / Software
# 浏览器：项目 / 工作实习 / 能力 / 软件

python generate.py --jd-file my-job.txt --fill-figma
# Optional: paste figma-fill-payload.json into Figma plugin
# 可选：插件粘贴 figma-fill-payload.json
```

---

## License & contributing · 开源与贡献

Open source — clone, use, adapt. Issues & PRs welcome. Without Figma you still get `resume.txt`, `resume.json`, `cover_letter.md`.

开源项目，欢迎克隆使用与 PR。即使不用 Figma，也可完整使用文本与 JSON 输出。
