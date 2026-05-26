# ai-weekly 快速上手示例

## 最简单的用法

```bash
cd your-project
ai-weekly
```

就这一行，完事。

## 输出到飞书

```bash
ai-weekly generate --format feishu > feishu.json
# 然后用 curl 发到飞书 webhook:
# curl -X POST -H "Content-Type: application/json" -d @feishu.json YOUR_WEBHOOK_URL
```

## 输出到钉钉

```bash
ai-weekly generate --format dingtalk > dingtalk.json
# curl -X POST -H "Content-Type: application/json" -d @dingtalk.json YOUR_WEBHOOK_URL
```

## GitHub Action 自动周报

把 `.github/workflows/weekly-report.yml` 复制到你的仓库里就行。

可选：在仓库 Settings > Secrets 里加 `AI_API_KEY` 和 `AI_BASE_URL` 启用 AI 润色。

推荐免费 API：
- 智谱: BASE_URL=`https://open.bigmodel.cn/api/paas/v4`, MODEL=`glm-4-flash`
- SiliconFlow: BASE_URL=`https://api.siliconflow.cn/v1`, MODEL=`Qwen/Qwen2.5-7B-Instruct`
