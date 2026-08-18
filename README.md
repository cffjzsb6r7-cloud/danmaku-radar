# 弹幕雷达 Danmaku Radar

> 面向内容创作者、运营与求职者的 B站热度雷达：每周自动抓取 B站真实热榜，把「最近什么火、为什么火、怎么抄作业」一次讲清楚。

弹幕雷达是一个**全栈、自动更新、可对外使用**的开源项目：

- 自动抓取 B站真实数据（公开接口），每 6 小时更新一次；
- 内容热榜 Top 20：按「近 7 天点赞增量」排序，附播放 / 点赞 / 评论 / 收藏数据与直达原视频链接；
- 每张视频卡片提供「下载源视频」与「同类学习」两个入口；
- 跨平台学习搜索台：输入关键词，一键跳转 8 个平台搜索同类内容；
- 弹幕热词、评论区 TOP 摘要、爆款多维度拆解、一键生成克隆脚本；
- 中英双语邮件周报订阅、暗色模式、PWA 可安装到桌面。

## 在线体验

- 网站：https://cffjzsb6r7-cloud.github.io/danmaku-radar/
- 数据接口：https://danmaku-radar-api.onrender.com/api/trends

## 功能一览

| 功能 | 说明 |
| --- | --- |
| 内容热榜 Top 20 | 近 7 天点赞增量最高的 B站视频，附完整数据与直达链接 |
| 下载源视频 | 一键打开原视频 / 复制链接 / 复制 BV 号，并给出 yt-dlp 等下载指引 |
| 同类学习 | 按视频标题自动生成 8 平台搜索入口：B站 / YouTube / 抖音 / 小红书 / 快手 / 微博 / X / Reddit |
| 学习搜索台 | 手动输入任意关键词，一键生成跨平台学习搜索链接 |
| 弹幕热词 | 每个上榜视频的弹幕高频词与出现次数 |
| 评论区 TOP | 每个上榜视频的热门评论与点赞数 |
| 拆解爆款 | 从热度、剪辑、画面风格、技术热词、话题、评论、作者账号等维度专业拆解 |
| 克隆选题 | 基于原爆款与作者账号，生成完整可执行的视频脚本 |
| 百度热搜 | 独立区块展示当前热搜词，紧跟全网热点 |
| 邮件周报 | 中英双语，每周自动推送（SMTP 可配置） |
| PWA / 暗色模式 | 可安装到桌面，支持深色模式 |

## 技术栈

- 前端：原生 HTML / CSS / JavaScript · PWA · GitHub Pages
- 后端：Python · FastAPI · SQLite · SMTP 邮件
- 爬虫：B站公开接口，内置频率控制与降级策略
- 工程化：GitHub Actions 定时抓取 · pytest 单元测试 · Docker / Render 部署 · 可观测性 API

## 目录结构

```text
danmaku-radar/
├── backend/            # FastAPI 后端：抓取、入库、周报、邮件、API
├── website/            # 前端网站（静态资源，PWA）
├── crawler/            # 爬虫适配层
├── data/               # 真实数据库 + 最新数据快照
├── examples/           # 示例数据
├── tests/              # pytest 单元测试
└── .github/workflows/  # CI + 每 6 小时自动抓取并发布
```

## 本地运行

1. 安装依赖：

```bash
pip install -r backend/requirements.txt
```

2. 抓取真实数据：

```bash
python backend/refresh.py
```

3. 启动后端：

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

4. 打开前端：直接访问 `website/index.html`，或运行 `python -m http.server 8000 --directory website`。

## API

| 接口 | 说明 |
| --- | --- |
| GET /api/trends | 内容热榜 + 弹幕热词 + 评论摘要 + 百度热搜 |
| GET /api/history | 历史数据快照 |
| GET /api/stats | 运行统计（可观测性） |
| GET /api/health | 健康检查 |
| POST /api/subscribe | 邮件订阅周报 |
| GET /api/digests | 历史周报列表 |

## 自动更新

GitHub Actions 每 6 小时自动执行一次：抓取 B站真实热榜 → 更新 SQLite 数据库 → 提交数据快照 → 重新发布 GitHub Pages；后端部署在 Render，保证网站与接口始终可用。


## 数据合规

- 数据来自 B站公开接口，仅用于个人学习与项目展示；
- 下载指引仅提供开源工具说明，不托管任何视频文件；
- 请遵守平台条款与相关法律法规。

## Roadmap

- 个性化订阅：按分区 / UP 主订阅周报
- 弹幕情感分析：判断观众对视频的情绪倾向
- 多平台扩展：YouTube / 抖音 / 小红书热榜接入

## License

MIT © 2026 Danmaku Radar
