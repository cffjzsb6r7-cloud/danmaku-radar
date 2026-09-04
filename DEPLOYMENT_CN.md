# 弹幕雷达：独立域名与微信小程序上线

仓库已经包含可运行的 FastAPI 后端。之前页面里的 `https://danmaku-radar-api.onrender.com` 目前返回 `404 / no-server`，因此线上网页会自动显示 `data/latest.json` 的静态快照。下面的部署会把 API、网站和 SQLite 数据放到同一个服务，并为数据库配置持久化磁盘。

## 推荐架构

```text
danmaku-radar.cn（网站 + API，同源）
  ├── GET  /api/trends
  ├── GET  /api/health
  ├── POST /api/subscribe
  └── POST /api/refresh（需要 DANMAKU_REFRESH_TOKEN）
```

单域名模式由 `DANMAKU_SERVE_WEB=true` 开启。`website/api-config.js` 会在 GitHub Pages 上继续使用远端 API，在自定义域名上自动使用当前域名，因此不需要改 `app.js`。

## 方案 A：Render（最快验证）

1. 把仓库推送到自己的 GitHub 仓库，在 Render 选择 **New > Blueprint**，导入仓库根目录的 `render.yaml`。
2. `render.yaml` 使用 Starter 计划和 1GB persistent disk。免费计划没有持久化磁盘，重启后订阅邮箱会丢失，不适合正式小程序。
3. 在 Render 环境变量中填写：
   - `DANMAKU_CORS`：`https://你的域名`（多个来源用英文逗号分隔）。
   - `DANMAKU_REFRESH_TOKEN`：随机长字符串，例如 `openssl rand -hex 32` 的结果。
   - `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASS` / `SMTP_FROM`：需要周报邮件时再填。
4. 部署后验证：

```bash
curl https://你的服务.onrender.com/api/health
curl https://你的服务.onrender.com/api/trends
```

`/api/health` 返回 `ok: true` 且 `posts` 大于 0，说明抓取和数据库都可用。首次没有数据时，运行一次：

```bash
curl -X POST https://你的服务.onrender.com/api/refresh \
  -H "Authorization: Bearer 你的DANMAKU_REFRESH_TOKEN"
```

5. 在 Render 的 Custom Domains 绑定 `api.你的域名` 或 `你的域名`。Render 会签发 HTTPS 证书。若网站仍部署在 GitHub Pages，只需将 `website/api-config.js` 中的 API 地址改为这个自定义 API 域名；若使用本服务托管网站，则直接访问该域名即可。

## 方案 B：中国大陆云服务器（正式小程序）

微信小程序要求 request 合法域名使用 HTTPS；面向中国大陆用户还应准备已备案的域名。建议购买腾讯云/阿里云轻量服务器，使用 Docker 部署，并在域名控制台添加 `A` 记录：`api.example.cn -> 服务器公网 IP`。

```bash
git clone https://github.com/你的账号/danmaku-radar.git
cd danmaku-radar
docker build -t danmaku-radar .
docker run -d --name danmaku-radar \
  -p 8000:8000 \
  -v /opt/danmaku-data:/var/data \
  -e DANMAKU_CORS=https://example.cn \
  -e DANMAKU_SERVE_WEB=true \
  -e DANMAKU_DB=/var/data/danmaku.db \
  -e DANMAKU_REFRESH_TOKEN=替换为随机长字符串 \
  danmaku-radar
```

再用 Nginx/Caddy 将 `https://example.cn` 反向代理到 `127.0.0.1:8000`，并自动申请 Let's Encrypt 证书。生产环境不要直接暴露 8000 端口。小程序后台填入：开发 > 开发管理 > 开发设置 > 服务器域名 > `request 合法域名`，添加 `https://example.cn`（不能带路径、端口或通配符）。如果小程序使用 `web-view`，还要在业务域名中添加同一个 HTTPS 域名。

## 微信小程序接入

小程序端不能调用 `127.0.0.1` 或 HTTP 地址。将 API 基址放在一个配置文件中：

```js
const API_BASE = 'https://example.cn';

wx.request({
  url: `${API_BASE}/api/trends`,
  success(res) {
    if (res.data && res.data.ok !== false) {
      // res.data.content_rank / topic_rank / hot_search
    }
  }
});
```

订阅接口：

```js
wx.request({
  url: `${API_BASE}/api/subscribe`,
  method: 'POST',
  header: { 'content-type': 'application/json' },
  data: { email, lang: 'both', categories: '' }
});
```

小程序审核前还需要：主体认证、隐私政策与用户同意流程、备案域名、HTTPS 证书，以及在小程序后台配置合法域名。邮箱订阅不是微信登录；如果后续需要“微信用户收藏跨设备同步”，再增加 `wx.login` + `jscode2session` 用户表和登录态，不要把 `AppSecret` 放在前端。

## 每日抓取与周报

GitHub Actions 的 `weekly-digest.yml` 仍负责每日抓取、生成 `data/latest.json` 和发送邮件。正式使用时建议把 `DANMAKU_DB` 指向持久化磁盘，并把 SMTP 变量放在 GitHub Secrets/Render Secrets，不要提交 `.env`。`POST /api/refresh` 已支持 Bearer token，避免被公开调用反复触发 B 站抓取。

## 本地验证

```bash
python -m pip install -r backend/requirements-dev.txt
python -m compileall backend
python -m pytest tests -q
uvicorn backend.app.main:app --reload --port 8000
```

开启单域名模式：

```bash
# PowerShell
$env:DANMAKU_SERVE_WEB = "true"
uvicorn backend.app.main:app --reload --port 8000
```

然后访问 `http://127.0.0.1:8000/` 和 `http://127.0.0.1:8000/api/health`。
