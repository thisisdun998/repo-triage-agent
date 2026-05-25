# Repo Triage Agent

Repo Triage Agent 是一个面向开源维护者的轻量级 Agent。它读取 GitHub 仓库的 README、目录结构、open issues 和最近提交记录，然后生成一份维护建议报告，帮助维护者快速判断项目状态、问题优先级和下一步行动。

这个项目的目标不是做一个复杂平台，而是展示一个清晰的 Agent 工作流：

1. **Perceive**：采集仓库 README、文件树、issues、commits。
2. **Analyze**：判断项目类型、README 完整度、issue 类型。
3. **Plan**：挑选适合优先处理的问题和新手友好任务。
4. **Act**：生成 `MAINTAINER_REPORT.md` 维护建议报告。

## Features

- 支持 GitHub URL 或 `owner/repo` 输入。
- 支持内置离线示例，方便无网络环境演示。
- 按 `bug`、`feature`、`docs`、`question`、`maintenance` 分类 issue。
- 识别 `good first issue`、文档类、简单修复类的新手友好任务。
- 输出 Markdown 报告，可直接提交到仓库或用于项目维护记录。
- 仅使用 Python 标准库，无第三方依赖。

## Quick Start

运行内置示例：

```bash
python3 -m repo_triage_agent --sample
```

生成样例报告：

```bash
python3 -m repo_triage_agent --sample --output MAINTAINER_REPORT.md
```

分析真实 GitHub 仓库：

```bash
python3 -m repo_triage_agent https://github.com/openai/codex --output MAINTAINER_REPORT.md
```

如果遇到 GitHub API rate limit，可以设置 token：

```bash
export GITHUB_TOKEN=your_token_here
```

## Example Output

报告会包含：

- 仓库类型和 README 完整度。
- Agent reasoning 过程。
- issue 分类统计。
- 新手友好任务推荐。
- 最近提交信号。
- 推荐下一步行动。

## Tests

```bash
python3 -m unittest discover -s tests
```

## Application Description

如果需要在模型申请表里描述项目，可以使用这段：

> 我构建了一个面向开源项目维护者的 GitHub Repo Triage Agent。它可以读取指定 GitHub 仓库的 README、目录结构、open issues 和最近提交记录，自动识别项目状态、归类待处理问题，并生成维护建议报告。核心逻辑包含多步信息收集、结构化分析、任务优先级判断和 Markdown 报告生成，帮助维护者更快发现适合修复的问题、识别文档缺口，并规划下一步迭代。该项目已实现可运行 CLI、离线示例和自动化测试，方便在 GitHub 上复现和扩展。

## Project Scope

当前版本刻意保持小而清楚：它是一个 deterministic agent，不依赖外部 LLM。后续可以接入 MiMo、GPT 或其他模型，把 issue 归因、优先级解释和行动建议升级为更自然的长链推理。
