# -*- coding: utf-8 -*-
"""弹幕雷达核心单元测试（真实数据库用临时文件，不影响线上数据）"""
import os
import sys
import tempfile

os.environ["DANMAKU_DB"] = os.path.join(tempfile.gettempdir(), "danmaku-radar-test.db")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.app import crawler, db, digest  # noqa: E402


def _wipe():
    conn = db.get_conn()
    for t in ["posts", "topics", "subscribers", "digests", "hot_search"]:
        conn.execute(f"DELETE FROM {t}")
    conn.execute("DELETE FROM meta WHERE key != 'last_fetch'")
    conn.commit()


def test_subscribe_roundtrip():
    _wipe()
    conn = db.get_conn()
    db.add_subscriber(conn, "a@b.com", "both", "搞笑")
    assert "a@b.com" in [s["email"] for s in db.active_subscribers(conn)]
    db.unsubscribe(conn, email="a@b.com")
    assert "a@b.com" not in [s["email"] for s in db.active_subscribers(conn)]


def test_duplicate_subscriber_updates():
    _wipe()
    conn = db.get_conn()
    db.add_subscriber(conn, "dup@b.com", "both", "")
    db.add_subscriber(conn, "dup@b.com", "both", "科技")
    subs = [s for s in db.active_subscribers(conn) if s["email"] == "dup@b.com"]
    assert subs and subs[0]["categories"] == "科技"
    db.unsubscribe(conn, email="dup@b.com")


def test_meta_roundtrip():
    _wipe()
    conn = db.get_conn()
    db.set_meta(conn, "danmaku_words", '[]')
    assert db.get_meta(conn, "danmaku_words") == "[]"


def test_digest_bilingual():
    posts = [{"rank": 1, "title": "t", "category": "c", "url": "https://x",
              "stats": {"likes": 1, "like_growth": 2, "comments": 3, "saves": 4, "views": 5}}]
    topics = [{"rank": 1, "topic": "#a", "post_count": 1, "post_growth": 1, "trend": "+100%"}]
    md = digest.build_bilingual(posts, topics, "w",
                                hot=[{"rank": 1, "word": "h"}],
                                highlights=[{"title": "t", "like_growth": 2}],
                                danmaku=[{"word": "弹", "count": 1}])
    assert "必看" in md and "English" in md and "弹" in md


def test_html_digest():
    posts = [{"rank": 1, "title": "t", "category": "c", "url": "https://x",
              "stats": {"likes": 1, "like_growth": 2, "comments": 3, "saves": 4, "views": 5}}]
    topics = [{"rank": 1, "topic": "#a", "post_count": 1, "post_growth": 1, "trend": "+100%"}]
    html = digest.build_html(posts, topics, "w", hot=[{"word": "h"}],
                             highlights=[{"title": "t", "like_growth": 2}],
                             danmaku=[{"word": "弹", "count": 1}])
    assert "Danmaku Radar" in html and "弹" in html


def test_baidu_parse(monkeypatch):
    sample = {
        "data": {"cards": [{"component": "tabTextList", "content": [
            {"content": [{"word": "热搜A", "url": "https://x"}, {"word": "热搜B", "url": "https://y"}]}
        ]}]}
    }
    monkeypatch.setattr(crawler, "fetch_json", lambda url, timeout=15: sample)
    out = crawler.fetch_baidu_hot(5)
    assert out[0]["word"] == "热搜A" and out[1]["word"] == "热搜B"
