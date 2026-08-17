# -*- coding: utf-8 -*-
"""真实数据库（SQLite）· 弹幕雷达
表：posts / topics / subscribers / digests / meta
"""
import json
import os
import sqlite3
import uuid
from datetime import datetime

DB_PATH = os.environ.get(
    "DANMAKU_DB",
    os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "danmaku.db")),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  week TEXT NOT NULL,
  source_id INTEGER,
  rank INTEGER,
  title TEXT,
  author TEXT,
  url TEXT,
  category TEXT,
  topics TEXT DEFAULT '[]',
  score INTEGER DEFAULT 0,
  prev_score INTEGER DEFAULT 0,
  like_growth INTEGER DEFAULT 0,
  comments INTEGER DEFAULT 0,
  views INTEGER DEFAULT 0,
  saves INTEGER DEFAULT 0,
  summary TEXT DEFAULT '',
  comment_summary TEXT DEFAULT '',
  published_at TEXT DEFAULT '',
  fetched_at TEXT
);
CREATE TABLE IF NOT EXISTS topics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  week TEXT NOT NULL,
  rank INTEGER,
  topic TEXT,
  post_count INTEGER DEFAULT 0,
  prev_count INTEGER DEFAULT 0,
  post_growth INTEGER DEFAULT 0,
  trend TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS subscribers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE,
  lang TEXT DEFAULT 'both',
  token TEXT,
  active INTEGER DEFAULT 1,
  subscribed_at TEXT
);
CREATE TABLE IF NOT EXISTS digests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  week TEXT,
  lang TEXT,
  content TEXT,
  sent_to INTEGER DEFAULT 0,
  sent_at TEXT
);
CREATE TABLE IF NOT EXISTS hot_search (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  week TEXT NOT NULL,
  rank INTEGER,
  word TEXT,
  url TEXT,
  hot_score INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT
);
"""


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(subscribers)").fetchall()]
    if "categories" not in cols:
        conn.execute("ALTER TABLE subscribers ADD COLUMN categories TEXT DEFAULT ''")
    pcols = [r[1] for r in conn.execute("PRAGMA table_info(posts)").fetchall()]
    for col, ddl in {
        "desc": "TEXT DEFAULT ''",
        "duration": "INTEGER DEFAULT 0",
        "author_mid": "INTEGER DEFAULT 0",
        "author_fans": "INTEGER DEFAULT 0",
        "author_archives": "INTEGER DEFAULT 0",
        "author_level": "INTEGER DEFAULT 0",
        "author_sign": "TEXT DEFAULT ''",
        "top_comments": "TEXT DEFAULT '[]'",
        "danmaku_words": "TEXT DEFAULT '[]'",
    }.items():
        if col not in pcols:
            conn.execute("ALTER TABLE posts ADD COLUMN {} {}".format(col, ddl))
    conn.commit()
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_week ON posts(week)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_topics_week ON topics(week)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sub_email ON subscribers(email)")
    return conn


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_prev_scores(conn):
    rows = conn.execute(
        "SELECT source_id, score FROM posts WHERE week != (SELECT MAX(week) FROM posts) ORDER BY id DESC"
    ).fetchall()
    out = {}
    for r in rows:
        out.setdefault(r["source_id"], r["score"])
    return out


def get_prev_topic_counts(conn):
    rows = conn.execute(
        "SELECT topic, post_count FROM topics WHERE week != (SELECT MAX(week) FROM topics) ORDER BY id DESC"
    ).fetchall()
    out = {}
    for r in rows:
        out.setdefault(r["topic"], r["post_count"])
    return out


def upsert_week(conn, week, posts, topics, hot_search=None):
    prev_scores = get_prev_scores(conn)
    prev_topic = get_prev_topic_counts(conn)
    cur = conn.cursor()
    # 同一周先清后插：每周只保留一份快照
    cur.execute("DELETE FROM posts WHERE week=?", (week,))
    cur.execute("DELETE FROM topics WHERE week=?", (week,))
    if "hot_search" in posts.__class__.__name__.lower():
        pass
    conn.commit()
    for p in posts:
        prev = prev_scores.get(p.get("source_id"), 0)
        cur.execute(
            """INSERT INTO posts
               (week, source_id, rank, title, author, url, category, topics, score, prev_score,
                like_growth, comments, views, saves, summary, comment_summary, published_at, fetched_at,
                desc, duration, author_mid, author_fans, author_archives, author_level, author_sign,
                top_comments, danmaku_words)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (week, p.get("source_id"), p.get("rank"), p.get("title"), p.get("author"), p.get("url"),
             p.get("category"), json.dumps(p.get("topics", []), ensure_ascii=False),
             p.get("score", 0), prev, max(0, p.get("score", 0) - prev),
             p.get("comments", 0), p.get("views", 0), p.get("saves", 0),
             p.get("summary", ""), p.get("comment_summary", ""), p.get("published_at", ""), now(),
             p.get("desc", ""), p.get("duration", 0), p.get("author_mid", 0), p.get("author_fans", 0),
             p.get("author_archives", 0), p.get("author_level", 0), p.get("author_sign", ""),
             json.dumps(p.get("top_comments", []), ensure_ascii=False),
             json.dumps(p.get("danmaku_words", []), ensure_ascii=False)),
        )
    for i, t in enumerate(topics, 1):
        topic = t["topic"] if isinstance(t, dict) else t[0]
        count = t["count"] if isinstance(t, dict) else t[1]
        prev = prev_topic.get(topic, 0)
        growth = max(0, int(count))
        trend = ("+" + str(round(growth / prev * 100)) + "%") if prev else "新增"
        cur.execute(
            """INSERT INTO topics (week, rank, topic, post_count, prev_count, post_growth, trend)
               VALUES (?,?,?,?,?,?,?)""",
            (week, i, topic, count, prev, growth, trend),
        )
    # 百度热搜（尽力而为）
    cur.execute("DELETE FROM hot_search WHERE week=?", (week,))
    for i, h in enumerate(hot_search or [], 1):
        cur.execute("INSERT INTO hot_search (week, rank, word, url, hot_score) VALUES (?,?,?,?,?)",
                    (week, i, h.get("word", ""), h.get("url", ""), int(h.get("hot_score") or 0)))
    conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('last_fetch', ?)", (now(),))
    conn.commit()


def latest_posts(conn, limit=20):
    rows = conn.execute(
        "SELECT * FROM posts WHERE week = (SELECT MAX(week) FROM posts) ORDER BY rank ASC LIMIT ?",
        (limit,),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["topics"] = json.loads(d.get("topics") or "[]")
        d["top_comments"] = json.loads(d.get("top_comments") or "[]")
        d["danmaku_words"] = json.loads(d.get("danmaku_words") or "[]")
        out.append(d)
    return out


def latest_hot_search(conn, limit=20):
    rows = conn.execute(
        "SELECT * FROM hot_search WHERE week = (SELECT MAX(week) FROM hot_search) ORDER BY rank ASC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def latest_topics(conn, limit=20):
    rows = conn.execute(
        "SELECT * FROM topics WHERE week = (SELECT MAX(week) FROM topics) ORDER BY rank ASC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def latest_week(conn):
    r = conn.execute("SELECT MAX(week) AS w FROM posts").fetchone()
    return r["w"] if r and r["w"] else None


def last_fetch(conn):
    r = conn.execute("SELECT value FROM meta WHERE key='last_fetch'").fetchone()
    return r["value"] if r else None


def add_subscriber(conn, email, lang="both", categories=""):
    token = uuid.uuid4().hex[:16]
    conn.execute(
        """INSERT INTO subscribers (email, lang, categories, token, active, subscribed_at)
           VALUES (?,?,?,?,1,?)
           ON CONFLICT(email) DO UPDATE SET active=1, lang=excluded.lang, categories=excluded.categories""",
        (email.strip().lower(), lang, categories, token, now()),
    )
    conn.commit()
    return token


def unsubscribe(conn, email=None, token=None):
    if token:
        conn.execute("UPDATE subscribers SET active=0 WHERE token=?", (token,))
    elif email:
        conn.execute("UPDATE subscribers SET active=0 WHERE email=?", (email.strip().lower(),))
    conn.commit()


def active_subscribers(conn):
    rows = conn.execute("SELECT * FROM subscribers WHERE active=1").fetchall()
    return [dict(r) for r in rows]


def save_digest(conn, week, lang, content, sent_to):
    conn.execute("INSERT INTO digests (week, lang, content, sent_to, sent_at) VALUES (?,?,?,?,?)",
                 (week, lang, content, sent_to, now()))
    conn.commit()


def get_digests(conn, limit=10):
    rows = conn.execute("SELECT * FROM digests ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def week_summary(conn, weeks=8):
    """历史趋势：每周 总点赞 / 条数 / 最热视频"""
    rows = conn.execute(
        """SELECT week, COUNT(*) AS posts, SUM(score) AS total_likes, MAX(score) AS top_score
           FROM posts GROUP BY week ORDER BY week ASC LIMIT ?""",
        (weeks,),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        top = conn.execute(
            "SELECT title FROM posts WHERE week=? AND score=? LIMIT 1", (r["week"], r["top_score"])
        ).fetchone()
        d["top_title"] = top["title"] if top else ""
        out.append(d)
    return out


def set_meta(conn, key, value):
    conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)", (key, value))
    conn.commit()


def get_meta(conn, key, default=None):
    r = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default
