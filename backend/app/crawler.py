# -*- coding: utf-8 -*-
"""真实数据源：B站（bilibili）公开排行榜接口（加固版）
- 内置访客 cookie（buvid3）引导以通过风控
- 请求重试 + 指数退避；失败抛 CrawlerError，由上层降级为保留旧数据
"""
import re
import time
from collections import Counter
from datetime import date, timedelta

import requests

RANKING = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all"
TAGS = "https://api.bilibili.com/x/tag/archive/tags?bvid={bvid}"
POPULAR = "https://api.bilibili.com/x/web-interface/popular?ps=50&pn={pn}"
BAIDU_HOT = "https://top.baidu.com/api/board?platform=wise&tab=realtime"
COMMENTS = "https://api.bilibili.com/x/v2/reply?type=1&oid={oid}&ps=5&sort=2"
CARD = "https://api.bilibili.com/x/web-interface/card?mid={mid}"
HOME = "https://www.bilibili.com/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
}
MAX_RETRY = 3
STOP_CHARS = set("的了是就在和与及或不把被为有这那也都还要我们你们他们一个可以因为所以但是然后进行通过对于".split())


class CrawlerError(Exception):
    """抓取失败（风控/网络/接口异常）"""


_session = None


def get_session(force=False):
    global _session
    if _session is None or force:
        s = requests.Session()
        s.headers.update(HEADERS)
        try:
            s.get(HOME, timeout=20)
        except Exception:
            pass  # cookie 拿不到也继续尝试
        _session = s
    return _session


def fetch_json(url, timeout=15):
    last = None
    for attempt in range(MAX_RETRY):
        try:
            r = get_session(force=(attempt > 0)).get(url, timeout=timeout)
            r.raise_for_status()
            j = r.json()
            if j.get("code") not in (0, None):
                raise CrawlerError("B站接口 code={} msg={}".format(j.get("code"), j.get("message")))
            return j
        except CrawlerError:
            raise
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise CrawlerError("B站请求失败：{}".format(last))


def strip_html(s):
    return re.sub("<[^>]+>", " ", s or "").strip()


def fetch_top(limit=20):
    j = fetch_json(RANKING)
    lst = ((j.get("data") or {}).get("list")) or []
    if not lst:
        raise CrawlerError("B站排行榜返回为空（可能被风控）")
    return lst[:limit]




def fetch_video_tags(bvid):
    """真实视频标签（用户发布视频时携带的 tag）"""
    try:
        j = fetch_json(TAGS.format(bvid=bvid), timeout=10)
        lst = j if isinstance(j, list) else ((j or {}).get("data") or [])
        return [t.get("tag_name", "") for t in lst if t.get("tag_name")]
    except Exception:
        return []


def fetch_baidu_hot(limit=20):
    """百度热搜（真实公开接口，尽力而为；失败返回空列表，不影响主流程）"""
    try:
        j = fetch_json(BAIDU_HOT, timeout=10)
        out = []
        for card in (j.get("data") or {}).get("cards") or []:
            for group in (card.get("content") or []):
                for it in (group.get("content") or []):
                    word = it.get("word") or it.get("query")
                    if not word:
                        continue
                    out.append({"word": word, "url": it.get("url") or "",
                                "hot_score": it.get("hotScore") or it.get("heatScore") or 0})
        seen, res = set(), []
        for x in out:
            if x["word"] in seen:
                continue
            seen.add(x["word"])
            res.append(x)
            if len(res) >= limit:
                break
        return res
    except Exception:
        return []


def chinese_keywords(text, n=3):
    runs = re.findall(r"[\u4e00-\u9fff]{2,4}", text or "")
    freq = {}
    for g in runs:
        if len(g) < 2 or any(c in STOP_CHARS for c in g):
            continue
        freq[g] = freq.get(g, 0) + 1
    return [k for k, _ in sorted(freq.items(), key=lambda x: -x[1])[:n]]


def english_words(text, n=3):
    freq = Counter()
    for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", text or ""):
        lw = w.lower()
        if len(lw) < 3:
            continue
        freq[lw] += 1
    return [k for k, _ in freq.most_common(n)]




def _cjk_ngrams(text, n=4):
    runs = re.findall(r"[\u4e00-\u9fff]{2,}", text or "")
    out = []
    for run in runs:
        for ln in range(2, n + 1):
            for i in range(len(run) - ln + 1):
                g = run[i:i + ln]
                if len(g) >= 2 and not any(c in STOP_CHARS for c in g):
                    out.append(g)
    return out


def fetch_danmaku_words(bvid, cid=None, top_n=15, max_lines=800):
    try:
        if not cid:
            view = fetch_json("https://api.bilibili.com/x/web-interface/view?bvid=" + bvid, timeout=10)
            cid = ((view.get("data") or {}).get("cid")) or 0
        if not cid:
            return []
        r = get_session().get("https://api.bilibili.com/x/v1/dm/list.so?oid=" + str(cid), timeout=12)
        xml = r.content.decode("utf-8", "ignore")
        ms = re.findall(r"<d p=.{0,80}?>([^<]+)</d>", xml)[:max_lines]
        if not ms:
            return []
        counter = Counter()
        for line in ms:
            for g in _cjk_ngrams(line):
                counter[g] += 1
        return [{"word": w, "count": c} for w, c in counter.most_common(top_n)]
    except Exception:
        return []


def fetch_danmaku_for_top(posts, n_videos=3, top_n=15):
    words = []
    for p in posts[:n_videos]:
        m = re.search(r"/video/(BV[0-9A-Za-z]+)", p.get("url") or "")
        if m:
            words.extend(fetch_danmaku_words(m.group(1), top_n=top_n))
    counter = Counter()
    for w in words:
        counter[w["word"]] += w.get("count", 0)
    return [{"word": w, "count": c} for w, c in counter.most_common(top_n)]


def fetch_top_comments(oid, desc, limit=5):
    """返回 (热评列表, 评论区总结)；取不到时降级为简介"""
    try:
        j = fetch_json(COMMENTS.format(oid=oid), timeout=10)
        replies = ((j.get("data") or {}).get("replies")) or []
        out = []
        for c in replies[:limit]:
            text = strip_html(((c.get("content") or {}).get("message", "")))[:200]
            if not text:
                continue
            out.append({
                "user": ((c.get("member") or {}).get("uname")) or "匿名用户",
                "likes": c.get("like") or 0,
                "content": text,
            })
        if out:
            total = ((j.get("data") or {}).get("page") or {}).get("count", 0) or 0
            top = "；".join(x["content"][:50] for x in out[:2])
            return out, f"公开评论约 {total} 条，热评：{top}"
    except Exception:
        pass
    d = strip_html(desc)
    return [], ("（暂无公开评论）简介：" + d[:120])


def fetch_author_card(mid):
    """作者账号信息：粉丝数 / 投稿数 / 等级 / 签名（尽力而为）"""
    try:
        j = fetch_json(CARD.format(mid=mid), timeout=10)
        d = j.get("data") or {}
        c = d.get("card") or {}
        return {
            "author_fans": c.get("fans") or 0,
            "author_archives": d.get("archive_count") or 0,
            "author_level": ((c.get("level_info") or {}).get("current_level")) or 0,
            "author_sign": (c.get("sign") or "").strip()[:120],
        }
    except Exception:
        return {}


def build_summary(title, category, desc, topics, dm_words, comments, acct):
    """基于真实公开信息，自动生成「这条视频讲了什么」小结（本地规则，不调 AI）"""
    dm = "、".join(w["word"] for w in (dm_words or [])[:6]) or "暂无弹幕热词"
    cm = "；".join((c.get("content") or "")[:50] for c in (comments or [])[:3]) or "暂无热评"
    fans = acct.get("author_fans") or 0
    parts = [f"这是一条「{category}」类视频《{title}》"]
    if fans:
        parts.append(f"作者粉丝 {fans:,}（Lv.{acct.get('author_level') or '-'}，累计投稿 {acct.get('author_archives') or '-'} 条）")
    if desc:
        parts.append("简介：" + desc[:80])
    if topics:
        parts.append("话题标签：" + "、".join(topics[:5]))
    parts.append("弹幕热词：" + dm)
    parts.append("评论区热评：" + cm)
    return "；".join(parts)[:600]


def build_week(limit=20, week=None):
    items = fetch_top(limit)
    posts = []
    for i, it in enumerate(items, 1):
        stat = it.get("stat") or {}
        bvid = it.get("bvid", "")
        title = it.get("title", "") or ""
        tname = it.get("tname", "综合") or "综合"
        desc = strip_html(it.get("desc", ""))
        owner = it.get("owner") or {}
        topics = [tname] + chinese_keywords(title, 3) + english_words(title, 2)
        comments, csum = fetch_top_comments(it.get("aid"), desc)
        dm_words = fetch_danmaku_words(bvid, cid=it.get("cid"), top_n=10, max_lines=400)
        acct = fetch_author_card(owner.get("mid"))
        posts.append({
            "source_id": it.get("aid"),
            "rank": i,
            "title": title,
            "author": owner.get("name", ""),
            "url": "https://www.bilibili.com/video/" + bvid,
            "category": tname,
            "topics": topics,
            "score": stat.get("like", 0),
            "comments": stat.get("reply", 0),
            "views": stat.get("view", 0),
            "saves": stat.get("favorite", 0),
            "summary": build_summary(title, tname, desc, topics, dm_words, comments, acct),
            "desc": desc[:300],
            "duration": it.get("duration") or 0,
            "author_mid": owner.get("mid") or 0,
            "author_fans": acct.get("author_fans") or 0,
            "author_archives": acct.get("author_archives") or 0,
            "author_level": acct.get("author_level") or 0,
            "author_sign": (acct.get("author_sign") or "")[:120],
            "top_comments": comments,
            "danmaku_words": dm_words,
            "comment_summary": csum,
            "published_at": date.fromtimestamp(it["pubdate"]).isoformat() if it.get("pubdate") else "",
        })
    # 补充热门视频样本，统计「近 7 天话题新增发布量」（基于视频真实标签）
    samples = []
    try:
        for pn in (1, 2):
            j = fetch_json(POPULAR.format(pn=pn), timeout=12)
            samples.extend(((j.get("data") or {}).get("list")) or [])
    except Exception:
        pass
    seen = {p["source_id"] for p in posts}
    extra = [s for s in samples if s.get("aid") not in seen][:60]
    week_cut = date.today() - timedelta(days=7)
    tag_counter = Counter()
    by_id = {p["source_id"]: p for p in posts}
    for it in list(items) + extra:
        aid = it.get("aid")
        bvid = it.get("bvid", "")
        if not aid or not bvid:
            continue
        tags = fetch_video_tags(bvid)
        if not tags:
            continue
        if aid in by_id:
            by_id[aid]["topics"] = tags[:8]
        try:
            pub = date.fromtimestamp(it["pubdate"])
        except Exception:
            pub = None
        if pub and pub >= week_cut:
            for t in tags:
                tag_counter[t] += 1
        time.sleep(0.05)
    if tag_counter:
        topics = [{"topic": "#" + k, "count": c} for k, c in tag_counter.most_common(20)]
    else:
        # 标签抓取失败时的兜底：按分区 + 标题关键词统计
        counter = Counter()
        for p in posts:
            counter[p["category"]] += 1
            for t in p["topics"][1:]:
                counter[t] += 1
        topics = [{"topic": "#" + k, "count": c} for k, c in counter.most_common(20)]
    hot_search = fetch_baidu_hot(20)
    dm_counter = Counter()
    for p in posts:
        for w in p.get("danmaku_words") or []:
            dm_counter[w["word"]] += w.get("count", 0)
    danmaku_words = [{"word": w, "count": c} for w, c in dm_counter.most_common(15)]
    return {"week": week or default_week(), "posts": posts, "topics": topics, "hot_search": hot_search, "danmaku_words": danmaku_words}


def default_week():
    end = date.today()
    start = end - timedelta(days=6)
    return f"{start.isoformat()} ~ {end.isoformat()}"
