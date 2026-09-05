# CloudBase 免费测试函数

`index.js` 适配腾讯云 CloudBase 的 Node.js 20 HTTP 云函数：

- `GET /api/trends`：读取 GitHub Actions 生成的最新快照
- `GET /api/health`：健康检查
- `GET /api/history`：历史快照
- `GET /api/stats`：统计信息
- `POST /api/subscribe`：将邮箱临时写入 `/tmp`（函数重启后清空）

在 CloudBase 控制台的在线开发中打开 `index.js`，完整替换代码，保存后点击“部署”。函数监听端口为 9000，HTTP 网关路由 `/api` 需要开启路径透传。
