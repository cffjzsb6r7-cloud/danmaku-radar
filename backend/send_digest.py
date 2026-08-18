#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""弹幕雷达：向订阅者推送中英双语周报（支持按分区个性化订阅；SMTP 凭据走环境变量）
用法：SMTP_HOST=... SMTP_USER=... SMTP_PASS=... python backend/send_digest.py
"""
import json
import os
import pathlib
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import db, digest, emailer  # noqa: E402


def filter_by_categories(posts, categories):
    cats = [c.strip() for c in (categories or "").replace("，", ",").split(",") if c.strip()]
    if not cats:
        return posts
    hit = [p for p in posts if p.get("category") in cats]
    return hit or posts


def main():
    conn = db.get_conn()
    posts = db.latest_posts(conn)
    topics = db.latest_topics(conn)
    hot = db.latest_hot_search(conn)
    week = db.latest_week(conn)
    if not posts:
        print("数据库为空，先运行 python backend/refresh.py")
        return
    danmaku = json.loads(db.get_meta(conn, "danmaku_words") or "[]")
    highlights = sorted(
        [p for p in posts if p.get("like_growth", 0) > 0],
        key=lambda x: -x.get("like_growth", 0),
    )[:3]
    subs = [s for s in db.active_subscribers(conn) if s.get("email")]
    if not subs:
        print("暂无订阅者")
        return
    subject = f"弹幕雷达 · Danmaku Radar 周报 {week}"
    sent = 0
    for sub in subs:
        mine = filter_by_categories(posts, sub.get("categories", ""))
        url = os.environ.get("BACKEND_BASE", "https://danmaku-radar-api.onrender.com") + "/api/unsubscribe?token=" + (sub.get("token") or "")
        text = digest.build_bilingual(mine, topics, week, hot, highlights, danmaku, url)
        html = digest.build_html(mine, topics, week, hot, highlights, danmaku, url)
        sent += emailer.send_digest([sub["email"]], subject, text, html)
    db.save_digest(conn, week, "both", f"sent={sent}", sent)
    print(f"已发送 {sent}/{len(subs)} 封")


if __name__ == "__main__":
    main()
