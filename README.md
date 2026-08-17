# 弹幕雷达 Danmaku Radar

自动追踪 **B站（bilibili）热度** 的全栈项目：定时抓取 B站真实数据，展示内容热榜、话题热榜、弹幕热词与历史趋势，支持中英双语周报订阅。

## 功能

- 🔥 内容热榜 Top 20：真实视频标题 / 分区 / 播放 / 点赞 / 评论 / 收藏 + 直达原视频链接 + 评论摘要
- 🏷️ 话题热榜 Top 20：按「近 7 天该话题新增视频数」排序（统计自视频真实标签）
- 💬 弹幕热词：真实弹幕高频词
- 📈 历史趋势：每日快照自动累积，网页直接展示走势图
- 📧 订阅周报：中英双语，每周自动推送（SMTP 可配置）
- 🌙 暗色模式 / 📱 PWA 可安装
- ✅ pytest 单元测试 + CI + /api/stats 可观测性

## 技术栈

Python · FastAPI · SQLite · 爬虫（B站公开接口） · HTML/CSS/JS · GitHub Actions · GitHub Pages · PWA

## 目录结构

```text
danmaku-radar/
├── backend/            # 后端：抓取、入库、周报、邮件、API
├── website/            # 前端网站（静态，可离线回退）
├── data/               # 真实数据库 + 最新数据 + 历史趋势 + 周报
├── examples/           # 示例数据
└── .github/workflows/  # 自动任务：每 6 小时抓取并重新发布
```

## 自动更新

GitHub Actions 每 6 小时自动执行一次：抓取 B站真实热榜 → 更新数据库 → 生成最新数据与历史趋势 → 自动重新发布网站。

## 本地运行

1. 安装依赖：`pip install -r backend/requirements.txt`
2. 抓取真实数据：`python backend/refresh.py`
3. 启动后端：`uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`
4. 打开前端：`website/index.html`

主要 API：`/api/trends`（热榜） · `/api/history`（历史趋势） · `/api/subscribe`（订阅） · `/api/digests`（周报） · `/api/health`（健康检查）

## 数据合规

- 数据来自 B站公开接口，仅用于个人学习与项目展示。
- 爬虫已内置频率控制与降级策略；请遵守平台条款与相关法规。

## License

MIT © 2026 Danmaku Radar contributors
