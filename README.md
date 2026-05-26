<!--
╔══════════════════════════════════════════════════════════════════════╗
║  DreamSeed 种梦计划 — AI创造者大赛  官方 README 模板                ║
║                                                                      ║
║  使用说明：                                                          ║
║  1. 将本模板放在参赛仓库根目录 README.md 的顶部                       ║
║  2. 头图使用 DreamField 官方公开活动图片地址                         ║
║  3. 请保留 DREAMFIELD_README_HEADER_START / END 标识                 ║
║  4. 分割线以下供创作者自由编写项目内容                               ║
╚══════════════════════════════════════════════════════════════════════╝
-->

<!-- DREAMFIELD_README_HEADER_START -->

<p align="center">
  <a href="https://www.dreamfield.top">
    <img src="https://www.dreamfield.top/dream-field/contest-readme/assets/dreamseed-readme-banner.png" alt="DreamSeed 种梦计划参赛作品" width="100%" />
  </a>
</p>

<!-- DREAMFIELD_README_HEADER_END -->

---

# ai-weekly

用 Git 提交记录生成周报的命令行工具。

写周报烦不烦？每周一翻 git log，把 commit 凑成人话，再润色一遍发出去。
这个工具干的就是这件事：读 git log，整理成周报，完事。

配了 AI API 就用 AI 帮你润色归类，没配也能用，直接按 commit 分类输出。

## 环境要求

- Python 3.10 或更高版本
- Git（命令行能跑 `git --version` 就行）
- 操作系统：Windows / macOS / Linux 都支持

## 安装

### 方式一：pip 安装（推荐）

```bash
pip install ai-weekly
```

装完之后终端里就能直接用 `ai-weekly` 命令了。

### 方式二：从源码装

```bash
git clone https://github.com/a2328275243/ai-weekly.git
cd ai-weekly
pip install -e .
```

`-e` 是开发模式，改了代码不用重新装。

### 验证安装

```bash
ai-weekly --version
```

能看到版本号就说明装好了。如果提示找不到命令，检查一下 Python Scripts 目录有没有加到 PATH 里。

Windows 的话一般在：`C:\Users\你的用户名\AppData\Roaming\Python\Python3xx\Scripts`

## 用法

### 生成周报

```bash
# 最简单的用法：在 git 仓库里直接跑，默认取最近 7 天
ai-weekly generate

# 指定日期范围
ai-weekly generate --since 2026-05-19 --until 2026-05-25

# 多个仓库一起汇总
ai-weekly generate ./backend ./frontend ./infra

# 只统计某个人的提交
ai-weekly generate -a "张三"

# 保存到文件
ai-weekly generate -o report.md

# 补充 git 里没有的工作内容
ai-weekly generate -c "周三参加了技术评审"

# 不用 AI，纯粹按 commit 整理
ai-weekly generate --no-ai
```

### 输出格式

```bash
# 默认 Markdown
ai-weekly generate

# 飞书卡片 JSON（可直接用于飞书 webhook）
ai-weekly generate --format feishu

# 钉钉消息 JSON（可直接用于钉钉 webhook）
ai-weekly generate --format dingtalk

# 结构化 JSON（方便程序处理）
ai-weekly generate --format json
```

### 报告模板

```bash
# 默认模板
ai-weekly generate --template default

# 详细模板（带表格，每条 commit 都列出来）
ai-weekly generate --template detailed

# 简洁模板（一段话概括）
ai-weekly generate --template brief

# 自定义模板（Jinja2 格式）
ai-weekly generate --template ./my-template.md.j2
```

### GitHub PR 上下文

```bash
# 自动从 git remote 检测仓库，拉取 PR 信息丰富报告
ai-weekly generate --github

# 手动指定仓库
ai-weekly generate --github owner/repo
```

需要设置 `GITHUB_TOKEN` 环境变量（公开仓库不设也行，但有速率限制）。

### Web 预览

```bash
# 生成后直接在浏览器里预览
ai-weekly generate --preview

# 预览已有的报告文件
ai-weekly preview report.md
```

浏览器里可以切换 Markdown / 飞书 / 钉钉三种格式查看，带一键复制。

### 查看配置

```bash
ai-weekly config
ai-weekly config --json   # JSON 输出，方便脚本读取
```

## 配置 AI（可选）

不配 AI 也能用，只是输出比较朴素——直接列 commit 信息。
配了之后，AI 会把零散的 commit 归纳成 2~5 个工作项，读起来像人写的周报。

### 设置环境变量

Linux / macOS：
```bash
export AI_API_KEY="sk-你的密钥"
export AI_BASE_URL="https://api.deepseek.com/v1"
export AI_MODEL="deepseek-chat"
```

Windows CMD：
```cmd
set AI_API_KEY=sk-你的密钥
set AI_BASE_URL=https://api.deepseek.com/v1
set AI_MODEL=deepseek-chat
```

Windows PowerShell：
```powershell
$env:AI_API_KEY="sk-你的密钥"
$env:AI_BASE_URL="https://api.deepseek.com/v1"
$env:AI_MODEL="deepseek-chat"
```

想持久化的话写到 `.bashrc`、`.zshrc` 或系统环境变量里。

### 环境变量说明

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `AI_API_KEY` | 否 | 空 | 不填就走离线模式，不调 AI |
| `AI_BASE_URL` | 否 | `https://api.openai.com/v1` | API 地址 |
| `AI_MODEL` | 否 | `gpt-4o-mini` | 模型名称 |
| `AI_TIMEOUT` | 否 | `60` | 请求超时秒数 |

### 兼容哪些 AI 服务

只要是 OpenAI 格式的 chat completions 接口都行：

| 服务商 | BASE_URL | 推荐模型 | 免费额度 |
|--------|----------|----------|----------|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` | 注册送 500 万 tokens |
| SiliconFlow | `https://api.siliconflow.cn/v1` | `Qwen/Qwen2.5-7B-Instruct` | 注册送 2000 万 tokens，部分模型永久免费 |
| 智谱 AI | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` | glm-4-flash 免费不限量 |
| Groq | `https://api.groq.com/openai/v1` | `llama-3.1-8b-instant` | 免费，每分钟 30 请求 |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` | 付费 |
| 本地 Ollama | `http://localhost:11434/v1` | 你拉了什么就填什么 | 免费，本地跑 |
| 其他兼容服务 | 自己填 | 自己填 | - |

推荐新用户用 **智谱 glm-4-flash**（免费不限量）或 **SiliconFlow**（注册就送大量额度）。

## 效果演示

输入（你的 git log）：
```
feat: add user login with OAuth2
fix: pagination offset error on page 2+
refactor: extract db connection pool
docs: update deployment guide
chore: bump dependencies
```

输出（AI 模式下）：
```markdown
## 本周工作总结

### 主要完成
1. 完成用户登录模块，接入 OAuth2 认证流程
2. 修复分页偏移问题，影响第 2 页之后的数据展示
3. 重构数据库连接池，提升并发性能
4. 更新部署文档和依赖版本

### 关键数据
- 提交次数：5
- 修改文件：12
- 代码变更：+340 / -89
```

离线模式输出会更朴素，基本就是把 commit message 列出来加个统计。

## 命令参考

```
ai-weekly generate [REPOS...]   生成周报
  -s, --since TEXT              起始日期 YYYY-MM-DD（默认 7 天前）
  -u, --until TEXT              截止日期 YYYY-MM-DD（默认今天）
  -a, --author TEXT             按作者过滤
  -o, --output TEXT             输出到文件
  -c, --context TEXT            补充额外内容
  -t, --template TEXT           模板: default|detailed|brief|路径
  --format TEXT                 格式: markdown|feishu|dingtalk|json
  --github [OWNER/REPO]        拉取 GitHub PR 上下文
  --preview                     生成后浏览器预览
  --no-ai                       不调 AI，纯模板整理
  -q, --quiet                   安静模式，只输出内容

ai-weekly preview [FILE]        浏览器预览报告文件
ai-weekly config [--json]       查看 AI 配置状态
ai-weekly --version             查看版本
ai-weekly --help                查看帮助
```

## For AI Agents

这个工具对 AI agent（Claude Code、Codex、Cursor 等）友好：

```bash
# 安静模式 + JSON 输出，方便解析
ai-weekly generate --no-ai --quiet --format json

# 配置检查
ai-weekly config --json

# 退出码: 0=成功, 1=错误, 2=无数据
```

agent 直接通过 shell 调用即可，不需要额外集成。

## 项目结构

```
src/ai_weekly/
├── cli.py              # 命令行入口，所有参数处理
├── git_reader.py       # 读 git log，解析 commit
├── ai_generator.py     # 调 AI 生成报告 / fallback 到模板
├── renderer.py         # Jinja2 模板渲染
├── formatters.py       # 输出格式转换（飞书/钉钉/JSON）
├── github_context.py   # GitHub PR/Issue 数据拉取
├── web.py              # 本地预览服务器
├── templates/          # 内置 Jinja2 模板
│   ├── default.md.j2
│   ├── detailed.md.j2
│   └── brief.md.j2
└── static/
    └── preview.html    # 预览页面
```

## 常见问题

**Q: 提示 "git not found"**
A: 装个 Git。Windows 去 https://git-scm.com 下载安装，装完重开终端。

**Q: 提示找不到 ai-weekly 命令**
A: Python Scripts 目录没在 PATH 里。`pip show ai-weekly` 看装到哪了，把那个目录加到 PATH。

**Q: AI 生成超时**
A: 设大一点超时：`export AI_TIMEOUT=120`。或者换个快一点的模型。

**Q: Windows 终端显示乱码**
A: 用 Windows Terminal 或者把终端编码改成 UTF-8（`chcp 65001`）。

## 已实现

- [x] 飞书/钉钉消息格式适配
- [x] GitHub PR/Issue 上下文拉取
- [x] 自定义 Jinja2 报告模板
- [x] Web 浏览器预览界面
- [x] AI Agent 友好（--quiet + --format json）
- [x] 多种免费 AI 服务支持

## 后续想法

- Webhook 直接推送到飞书/钉钉群
- 定时自动生成（cron / GitHub Actions）
- DOCX 导出

## License

MIT
