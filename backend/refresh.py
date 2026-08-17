#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""弹幕雷达：抓取真实数据 → 写入真实数据库 → 生成 data/latest.json 与双语周报
用法：python backend/refresh.py
"""
import json
import pathlib
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import crawler, db, digest  # noqa: E402


def to_payload(conn):
    posts = db.latest_posts(conn)
    topics = db.latest_topics(conn)
    return {
        "week": db.latest_week(conn) or "",
        "last_fetch": db.last_fetch(conn) or "",
        "platform": "bilibili",
        "content_rank": [{
            "rank": p["rank"], "title": p["title"], "author": p["author"], "url": p["url"],
            "category": p["category"], "topics": p["topics"], "published_at": p["published_at"],
            "comment_summary": p["comment_summary"], "summary": p["summary"],
            "desc": p.get("desc", ""), "duration": p.get("duration", 0),
            "author_mid": p.get("author_mid", 0), "author_fans": p.get("author_fans", 0),
            "author_archives": p.get("author_archives", 0), "author_level": p.get("author_level", 0),
            "author_sign": p.get("author_sign", ""),
            "top_comments": p.get("top_comments") or [], "danmaku_words": p.get("danmaku_words") or [],
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


def main():
    conn = db.get_conn()
    print("[1/3] 正在抓取 B站真实排行榜...")
    data = crawler.build_week()
    print(f"      抓取完成：{len(data['posts'])} 条内容 / {len(data['topics'])} 个话题")
    print("[2/3] 写入真实数据库 (SQLite)...")
    db.upsert_week(conn, data["week"], data["posts"], data["topics"], data.get("hot_search"))
    db.set_meta(conn, "danmaku_words", json.dumps(data.get("danmaku_words") or [], ensure_ascii=False))
    payload = to_payload(conn)
    out = ROOT / "data" / "latest.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"      已写出 {out.relative_to(ROOT)}")
    history = {"weeks": db.week_summary(conn, 52)}
    hist_out = ROOT / "data" / "history.json"
    hist_out.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"      已写出 {hist_out.relative_to(ROOT)}（历史趋势 {len(history['weeks'])} 周）")
    print("[3/3] 生成中英双语周报...")
    md = digest.build_bilingual(payload["content_rank"], payload["topic_rank"], payload["week"])
    week_file = data["week"].replace(" ~ ", "-")
    report = ROOT / "data" / f"weekly-report-{week_file}.md"
    report.write_text(md, encoding="utf-8")
    print(f"      已写出 {report.relative_to(ROOT)}")
    print("完成 ✅（真实数据已入库）")


if __name__ == "__main__":
    try:
        main()
    except crawler.CrawlerError as e:
        print("⚠️  抓取失败（保留旧数据）：", e)
        sys.exit(0 if "--strict" not in sys.argv else 1)
