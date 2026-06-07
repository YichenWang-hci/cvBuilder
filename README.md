# cvBuilder MVP — Mac 跑通指南

**首次使用**：用 `onboard.py` 搭建个人资料库 → 用 `generate.py` 根据 JD 生成简历。

输入一段 JD → 终端打印完整简历文本，并保存到 `applications/` 文件夹。

---

## 第零步：搭建个人资料库（首次 / 新用户）

```bash
cd /Users/a1/Documents/cvBuilder
source .venv/bin/activate
python onboard.py --init          # 从 knowledge.example/ 复制空模板
python onboard.py                 # 按提示输入固定信息（任意语言）
```

`onboard.py` 会生成 `knowledge/profile.yaml`（姓名、联系方式、教育、语言等，自动存 de + en）。

**一次性粘贴模式**（不用逐题回答）：

```bash
python onboard.py --paste
# 粘贴全部个人信息 → Ctrl+D
```

已有 `profile.yaml` 只想更新固定信息、保留自我描述：

```bash
python onboard.py --keep-summaries
```

---

## 第一步：打开终端

`应用程序` → `实用工具` → **终端**  
或在 Cursor 里打开集成终端。

---

## 第二步：进入项目并激活环境

每次新开终端都要执行（复制粘贴，一行一行来）：

```bash
cd /Users/a1/Documents/cvBuilder
source .venv/bin/activate
```

成功时，命令行前面会出现 `(.venv)`。

如果还没有 `.venv`，先执行一次：

```bash
cd /Users/a1/Documents/cvBuilder
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 第三步：配置 API（推荐免费 Gemini）

```bash
cp .env.example .env
open -e .env
```

### 方案 A：Google Gemini（免费，推荐）

1. 打开 https://aistudio.google.com/apikey  
2. 登录 Google 账号 → Create API key  
3. 在 `.env` 里设置：

```
LLM_PROVIDER=gemini
GEMINI_API_KEY=你的Gemini密钥
GEMINI_MODEL=gemini-2.0-flash
```

**不需要信用卡。** 有每日免费额度，生成简历够用。

### 方案 B：Ollama（本地 100% 免费）

1. 安装 https://ollama.com  
2. 终端运行：

```bash
ollama pull llama3.2
```

3. `.env` 里设置：

```
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2
```

需要 Mac 有足够内存（建议 16GB+）。速度取决于电脑。

### 方案 C：OpenAI API（付费，Plus 会员不包含）

```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

需单独在 platform.openai.com 绑卡充值。

---

## 第四步：检查环境（不花钱）

```bash
python generate.py --dry-run
```

应看到：

```
Knowledge base loaded OK
  Projects: 4
    - ml-gesture
    ...
Dry run complete.
```

---

## 第五步：输入 JD，生成简历

### 方式 A：交互粘贴（推荐）

```bash
python generate.py
```

1. 终端提示 `Paste the job description below.`
2. **粘贴**整段 JD（Command+V）
3. 按 **Control + D** 结束输入（Mac 上是 Ctrl，不是 Cmd）
4. 等待 20–40 秒

### 方式 B：JD 放在文件里

```bash
python generate.py --jd-file ~/Desktop/jd.txt
```

### 方式 C：强制德语 / 英语

```bash
python generate.py --jd-file ~/Desktop/jd.txt --lang de
python generate.py --jd-file ~/Desktop/jd.txt --lang en
```

---

## 第六步：看输出

### 终端里会直接打印：

```
============================================================
CVBUILDER — GENERATED RESUME
============================================================
Language: de

[1] NAME
Yichen Wang

[2] SUMMARY
...

[3] EDUCATION
...

[4] PROJECTS
...

[5] CONTACT
...

[6] ABILITIES
...

[7] SOFTWARE
...

[8] LANGUAGES
...

============================================================
MATCH REPORT
============================================================
...

============================================================
COVER LETTER
============================================================
...
```

### 同时保存到文件夹：

```
applications/20260324-153045-application/
├── jd.txt
├── resume.txt       ← 与终端打印内容相同
├── resume.json
├── cover_letter.md
└── match_report.md
```

打开最新结果：

```bash
open applications/$(ls -t applications | head -1)/resume.txt
```

---

## 常见问题

| 问题 | 解决 |
|------|------|
| `OPENAI_API_KEY is not set` | 检查 `.env` 是否填了 key，是否在 `cvBuilder` 目录下运行 |
| `command not found: python` | 用 `python3 generate.py` |
| 粘贴 JD 后没反应 | 贴完后按 **Ctrl+D** |
| `zsh: command not found: #` | 不要把以 `#` 开头的说明文字粘贴进终端 |
| 没有 `(.venv)` | 先执行 `source .venv/bin/activate` |
| 想只要文件、不打印终端 | 加 `--quiet` |

---

## Figma 填充（MVP）

生成 `resume.json` 后，可导出 Figma 图层填充数据，在 Figma 模版里一键写入。

### 1. 一次性：导入 Figma 插件

1. 打开 Figma 桌面版  
2. **Plugins → Development → Import plugin from manifest…**  
3. 选择项目里的 `figma-plugin/manifest.json`

### 2. 生成填充数据

```bash
# 单独对已有 resume.json
python fill_figma.py applications/最新目录/resume.json

# 或生成简历时一并导出
python generate.py --jd-file ~/Desktop/jd.txt --fill-figma
```

会在同目录生成：

```
applications/.../
├── figma-fill-payload.json   ← 图层名 → 文本
└── figma-fill.js             ← 可选，给 Cursor use_figma 用
```

### 3. 在 Figma 里填充

1. 打开你的简历模版文件  
2. **Plugins → Development → cvBuilder Fill**  
3. 把 `figma-fill-payload.json` 的内容粘贴进文本框  
4. 点击 **Fill resume**

可选：在 `.env` 设置 `FIGMA_TEMPLATE_FRAME=你的A4 Frame名`，插件里填同一名字，只填充该 Frame 内图层。

### 4. 校验图层名（可选）

```bash
# .env 里配置 FIGMA_ACCESS_TOKEN + FIGMA_FILE_KEY
python fill_figma.py applications/.../resume.json --validate
```

### 复制到剪贴板（macOS）

```bash
python fill_figma.py applications/.../resume.json --copy-clipboard
# 或
python generate.py --fill-figma --copy-figma-clipboard
```

---

## 完整流程（复制这一组即可）

```bash
cd /Users/a1/Documents/cvBuilder
source .venv/bin/activate
python generate.py --dry-run
python generate.py
```

粘贴 JD → **Ctrl+D** → 等待 → 终端出现完整简历文本。
