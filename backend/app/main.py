# -*- coding: utf-8 -*-
"""弹幕雷达 · 后端 API（FastAPI，前后端分离，加固版）
接口：
  GET  /api/health        健康检查（含数据新鲜度）
  GET  /api/trends        最新内容热榜 + 话题热榜（空库自动抓取；抓取失败保留旧数据并标注 stale）
  POST /api/subscribe     订阅 {email, lang}
  POST /api/unsubscribe   退订 {email | token}
  GET  /api/digests       周报历史
  POST /api/refresh       立即刷新数据（失败返回 ok=False + 原因）
启动：uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
"""
import json
import os
import re
import secrets
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.app import crawler, db

app = FastAPI(title="弹幕雷达 API", version="1.2.0", description="B站真实热度数据 API")
_STARTED = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
_REFRESH_TOKEN = os.environ.get("DANMAKU_REFRESH_TOKEN", "").strip()
try:
    _STALE_HOURS = max(1, int(os.environ.get("DANMAKU_STALE_HOURS", "48")))
except ValueError:
    _STALE_HOURS = 48

_origins = os.environ.get("DANMAKU_CORS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class SubscribeIn(BaseModel):
    email: str
    lang: str = "both"
    categories: str = ""


class UnsubscribeIn(BaseModel):
    email: str = None
    token: str = None


def _refresh(silent=False):
    """抓取真实数据入库；失败抛 CrawlerError（由调用方降级）"""
    conn = db.get_conn()
    data = crawler.build_week()
    db.upsert_week(conn, data["week"], data["posts"], data["topics"], data.get("hot_search"))
    db.set_meta(conn, "danmaku_words", json.dumps(data.get("danmaku_words") or [], ensure_ascii=False))
    return data


def _trends_payload(conn):
    posts = db.latest_posts(conn)
    topics = db.latest_topics(conn)
    return {
        "week": db.latest_week(conn) or "",
        "last_fetch": db.last_fetch(conn) or "",
        "platform": "bilibili",
        "stale": False,
        "content_rank": [{
            "rank": p["rank"], "title": p["title"], "author": p["author"], "url": p["url"],
            "pic": p.get("pic", ""), "desc": p.get("desc", ""), "duration": p.get("duration", 0),
            "author_mid": p.get("author_mid", 0), "author_fans": p.get("author_fans", 0),
            "author_archives": p.get("author_archives", 0), "author_level": p.get("author_level", 0),
            "author_sign": p.get("author_sign", ""), "top_comments": p.get("top_comments") or [],
            "danmaku_words": p.get("danmaku_words") or [],
            "category": p["category"], "topics": p["topics"], "published_at": p["published_at"],
            "comment_summary": p["comment_summary"], "summary": p["summary"],
            "stats": {"likes": p["score"], "like_growth": p["like_growth"], "comments": p["comments"],
                      "saves": p["saves"], "views": p["views"]},
        } for p in posts],
        "hot_search": db.latest_hot_search(conn),
        "danmaku_words": json.loads(db.get_meta(conn, "danmaku_words") or "[]"),
        "highlights": sorted(
            [{
                "rank": p["rank"], "title": p["title"], "url": p["url"], "category": p["category"],
                "like_growth": p["like_growth"], "views": p["views"], "author": p["author"],
            } for p in posts if p["like_growth"] > 0],
            key=lambda x: -x["like_growth"],
        )[:3],
        "topic_rank": [{
            "rank": t["rank"], "topic": t["topic"], "post_count": t["post_count"],
            "post_growth": t["post_growth"], "trend": t["trend"],
        } for t in topics],
    }


def _is_stale(last_fetch):
    if not last_fetch:
        return True
    try:
        fetched = datetime.strptime(last_fetch, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - fetched).total_seconds() > _STALE_HOURS * 3600
    except (TypeError, ValueError):
        return True


def _check_refresh_token(request: Request):
    """Protect the expensive crawler endpoint when a token is configured."""
    if not _REFRESH_TOKEN:
        return
    supplied = request.headers.get("authorization", "")
    if supplied.lower().startswith("bearer "):
        supplied = supplied[7:].strip()
    supplied = supplied or request.headers.get("x-refresh-token", "")
    if not secrets.compare_digest(supplied, _REFRESH_TOKEN):
        raise HTTPException(status_code=401, detail="refresh authentication required")


@app.get("/api/health")
def health():
    conn = db.get_conn()
    posts = db.latest_posts(conn)
    return {
        "ok": True,
        "db": db.DB_PATH,
        "last_fetch": db.last_fetch(conn),
        "week": db.latest_week(conn),
        "posts": len(posts),
        "topics": len(db.latest_topics(conn)),
        "subscribers": len(db.active_subscribers(conn)),
        "stale": _is_stale(db.last_fetch(conn)) or not posts,
    }


@app.get("/api/trends")
def trends():
    conn = db.get_conn()
    if not db.latest_posts(conn):
        try:
            _refresh()
            conn = db.get_conn()
        except crawler.CrawlerError as e:
            return {"ok": False, "msg": "数据抓取失败：" + str(e), "content_rank": [], "topic_rank": []}
    payload = _trends_payload(conn)
    payload["stale"] = _is_stale(payload.get("last_fetch"))
    payload["ok"] = True
    return payload


@app.post("/api/refresh")
def refresh(request: Request):
    _check_refresh_token(request)
    try:
        data = _refresh()
        return {"ok": True, "week": data["week"], "posts": len(data["posts"]), "topics": len(data["topics"])}
    except crawler.CrawlerError as e:
        return {"ok": False, "msg": "刷新失败：" + str(e)}


@app.post("/api/subscribe")
def subscribe(body: SubscribeIn):
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        return {"ok": False, "msg": "邮箱格式不正确"}
    conn = db.get_conn()
    token = db.add_subscriber(conn, email, body.lang or "both", (body.categories or "").strip())
    return {"ok": True, "msg": "订阅成功", "token": token}


@app.get("/api/history")
def history(weeks: int = 8):
    conn = db.get_conn()
    return {"weeks": db.week_summary(conn, max(1, min(52, weeks)))}


@app.get("/api/stats")
def stats():
    conn = db.get_conn()
    topics = db.latest_topics(conn)
    return {
        "ok": True,
        "posts": len(db.latest_posts(conn)),
        "topics": len(topics),
        "hot_search": len(db.latest_hot_search(conn)),
        "danmaku_words": len(json.loads(db.get_meta(conn, "danmaku_words") or "[]")),
        "subscribers": len(db.active_subscribers(conn)),
        "digests": len(db.get_digests(conn, 1000)),
        "week": db.latest_week(conn),
        "last_fetch": db.last_fetch(conn),
        "top_topic": topics[0]["topic"] if topics else "",
        "uptime_since": _STARTED,
    }


@app.post("/api/unsubscribe")
def unsubscribe(body: UnsubscribeIn):
    conn = db.get_conn()
    db.unsubscribe(conn, email=body.email, token=body.token)
    return {"ok": True, "msg": "已退订"}


@app.get("/api/unsubscribe")
def unsubscribe_get(token: str = ""):
    conn = db.get_conn()
    db.unsubscribe(conn, token=token)
    return HTMLResponse(
        "<html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><title>已退订</title></head>"
        "<body style=\"font-family:system-ui;background:#F9F7F5;color:#231C33;display:grid;place-items:center;height:100vh;margin:0\">"
        "<div style=\"text-align:center;background:#fff;border:2px solid #231C33;border-radius:20px;padding:40px;max-width:420px\">"
        "<h1 style=\"font-size:22px;margin:0 0 10px\">已退订 ✅</h1>"
        "<p style=\"color:#736C83\">你已从弹幕雷达周报中退订。欢迎随时回来。</p>"
        "</div></body></html>",
        status_code=200,
    )


@app.get("/api/digests")
def digests(limit: int = 10):
    conn = db.get_conn()
    return {"digests": db.get_digests(conn, max(1, min(100, limit)))}


# A single-domain deployment can serve the existing static site from this API
# process. GitHub Pages deployments leave this disabled and use DANMAKU_API.
if os.environ.get("DANMAKU_SERVE_WEB", "0").lower() in {"1", "true", "yes"}:
    from fastapi.staticfiles import StaticFiles

    _website_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "website"))
    if os.path.isdir(_website_dir):
        app.mount("/", StaticFiles(directory=_website_dir, html=True), name="website")
else:
    @app.get("/")
    def root():
        return {"name": "danmaku-radar-api", "ok": True, "docs": "/docs", "health": "/api/health"}
