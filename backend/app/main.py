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
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.app import crawler, db

app = FastAPI(title="弹幕雷达 API", version="1.2.0", description="B站真实热度数据 API")
_STARTED = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
        "stale": not posts,
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
    payload["stale"] = False
    return payload


@app.post("/api/refresh")
def refresh():
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
    return {"weeks": db.week_summary(conn, weeks)}


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


@app.get("/api/digests")
def digests(limit: int = 10):
    conn = db.get_conn()
    return {"digests": db.get_digests(conn, limit)}
