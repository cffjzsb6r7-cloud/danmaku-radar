#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""弹幕雷达自测：数据库 / 数据载荷 / 订阅退订 / 双语周报 / 抓取（尽力而为）
用法：python backend/selftest.py
"""
import pathlib
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import crawler, db, digest  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(("✅" if ok else "❌"), name, detail)
    if not ok:
        FAILS.append(name)


def main():
    print("== 弹幕雷达自测 ==")
    conn = db.get_conn()
    check("数据库初始化", conn is not None, db.DB_PATH)

    payload = None
    try:
        from backend.app.main import _trends_payload
        payload = _trends_payload(conn)
        check("数据载荷生成", len(payload["content_rank"]) > 0, f"{len(payload['content_rank'])} 条内容")
    except Exception as e:
        check("数据载荷生成", False, str(e))

    # 抓取（尽力而为，网络失败仅警告）
    try:
        data = crawler.build_week()
        check("真实数据抓取（B站）", len(data["posts"]) > 0, f"{len(data['posts'])} 条")
    except crawler.CrawlerError as e:
        print("⚠️  真实数据抓取失败（网络/风控）：", e)

    # 订阅 / 退订
    db.add_subscriber(conn, "selftest@danmaku.dev", "both")
    subs = [s["email"] for s in db.active_subscribers(conn)]
    check("订阅入库", "selftest@danmaku.dev" in subs)
    db.unsubscribe(conn, email="selftest@danmaku.dev")
    subs = [s["email"] for s in db.active_subscribers(conn)]
    check("退订生效", "selftest@danmaku.dev" not in subs)

    # 双语周报
    posts = payload["content_rank"] if payload else db.latest_posts(conn)
    topics = db.latest_topics(conn)
    md = digest.build_bilingual(posts, topics, "2026-08-11 ~ 2026-08-17")
    check("双语周报生成", "#" in md and "English" in md)

    print("=" * 30)
    if FAILS:
        print("自测未全部通过：", ", ".join(FAILS))
        sys.exit(1)
    print("自测全部通过 ✅")


if __name__ == "__main__":
    main()
