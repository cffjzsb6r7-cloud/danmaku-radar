# -*- coding: utf-8 -*-
"""中英双语周报：纯文本 + HTML 邮件模板（含导读 / 弹幕热词）"""


def _num(n):
    try:
        return f"{int(n):,}"
    except Exception:
        return str(n or 0)



def _zh_hot(hot):
    if not hot:
        return "（本次未取到）"
    return " ｜ ".join(f"{h.get('rank')}. {h.get('word')}" for h in hot[:10])


def _hl_text(highlights):
    if not highlights:
        return "（暂无）"
    return " / ".join(f"{i + 1}. {h.get('title')}（▲{_num(h.get('like_growth'))}）" for i, h in enumerate(highlights[:3]))


def _dm_text(danmaku):
    if not danmaku:
        return "（暂无）"
    return "、".join(f"{w.get('word')}×{w.get('count')}" for w in danmaku[:10])


def build_zh(posts, topics, week, hot=None, highlights=None, danmaku=None, unsubscribe_url=""):
    lines = [f"# 📡 弹幕雷达 · 周报（中文）", "", f"统计周期：{week} ｜ 数据源：B站真实排行榜 + 百度热搜 + 真实弹幕", ""]
    lines.append("## ⭐ 本周必看 Top 3")
    lines.append(_hl_text(highlights))
    lines.append("")
    lines.append("## 🔥 内容热榜 Top 20")
    for p in posts:
        s = p.get("stats") or {}
        g = s.get("like_growth", 0)
        grow = f" ▲本周+{_num(g)}" if g else " 新增上榜"
        lines.append(f"{p.get('rank')}. **{p.get('title')}**{grow}")
        lines.append(f"   分区：{p.get('category')} ｜ 播放 {_num(s.get('views'))} ｜ 点赞 {_num(s.get('likes'))} ｜ 评论 {_num(s.get('comments'))} ｜ 收藏 {_num(s.get('saves'))}")
        lines.append(f"   直达：{p.get('url')}")
        if p.get("comment_summary"):
            lines.append(f"   摘要：{p.get('comment_summary')}")
    lines.append("")
    lines.append("## 🏷️ 话题热榜 Top 20")
    for t in topics:
        lines.append(f"{t.get('rank')}. {t.get('topic')} ▲本周+{t.get('post_growth')}（共 {t.get('post_count')}，{t.get('trend')}）")
    lines.append("")
    lines.append("## 💬 弹幕热词（真实弹幕聚合）")
    lines.append(_dm_text(danmaku))
    lines.append("")
    lines.append("## 🔥 百度热搜")
    lines.append(_zh_hot(hot))
    lines.append("")
    lines.append(("> 免费订阅 · 每周一推送 · [点此退订](" + unsubscribe_url + ")") if unsubscribe_url else "> 免费订阅 · 每周一推送 · 可随时退订")
    return "\n".join(lines)


def build_en(posts, topics, week, hot=None, highlights=None, danmaku=None, unsubscribe_url=""):
    lines = ["# 📡 Danmaku Radar · Weekly Digest (English)", "", f"Period: {week} ｜ Source: Bilibili (real) + Baidu Hot Search + Danmaku", ""]
    lines.append("## ⭐ Must-Watch Top 3")
    if highlights:
        lines.extend(f"{i + 1}. {h.get('title')} (▲+{_num(h.get('like_growth'))})" for i, h in enumerate(highlights[:3]))
    lines.append("")
    lines.append("## 🔥 Top 20 Hot Videos")
    for p in posts:
        s = p.get("stats") or {}
        g = s.get("like_growth", 0)
        grow = f" ▲+{_num(g)} this week" if g else " new"
        lines.append(f"{p.get('rank')}. {p.get('title')}{grow}")
        lines.append(f"   Category: {p.get('category')} ｜ Views: {_num(s.get('views'))} ｜ Likes: {_num(s.get('likes'))} ｜ Comments: {_num(s.get('comments'))} ｜ Favorites: {_num(s.get('saves'))}")
        lines.append(f"   Link: {p.get('url')}")
    lines.append("")
    lines.append("## 🏷️ Top 20 Topics")
    for t in topics:
        lines.append(f"{t.get('rank')}. {t.get('topic')} ▲+{t.get('post_growth')} this week (total {t.get('post_count')}, {t.get('trend')})")
    lines.append("")
    lines.append("## 💬 Danmaku Hot Words (real)")
    if danmaku:
        lines.append(", ".join(f"{w.get('word')}×{w.get('count')}" for w in danmaku[:10]))
    lines.append("")
    lines.append("## 🔥 Baidu Hot Search (real)")
    if hot:
        lines.append(", ".join(f"{h.get('rank')}. {h.get('word')}" for h in hot[:10]))
    lines.append("")
    lines.append(("> Free weekly digest · [Unsubscribe](" + unsubscribe_url + ")") if unsubscribe_url else "> Free weekly digest · Unsubscribe anytime")
    return "\n".join(lines)


def build_bilingual(posts, topics, week, hot=None, highlights=None, danmaku=None, unsubscribe_url=""):
    return build_zh(posts, topics, week, hot, highlights, danmaku, unsubscribe_url) + "\n\n---\n\n" + build_en(posts, topics, week, hot, highlights, danmaku, unsubscribe_url)


def _chip_spans(items, bg):
    return " ".join(
        f"<span style='display:inline-block;background:{bg};border:1px solid #231C33;border-radius:999px;padding:2px 10px;margin:3px 3px;font-size:12px;'>{item}</span>"
        for item in items[:12])


def build_html(posts, topics, week, hot=None, highlights=None, danmaku=None, unsubscribe_url=""):
    """简洁好看的 HTML 邮件（内联样式）"""
    def post_rows(posts):
        rows = []
        for p in posts[:10]:
            s = p.get("stats") or {}
            g = s.get("like_growth", 0)
            grow = f"<b style='color:#16BA5B'>▲ +{_num(g)}</b>" if g else "<span style='color:#736C83'>新增</span>"
            rows.append(
                f"<tr><td style='padding:10px 8px;border-bottom:1px solid #EEE;font-size:15px;'>"
                f"<b style='color:#5522FA;font-size:18px;'>{p.get('rank')}</b>&nbsp; <a href='{p.get('url')}' style='color:#231C33;text-decoration:none;'><b>{p.get('title')}</b></a> {grow}<br>"
                f"<span style='color:#736C83;font-size:13px;'>{p.get('category')} · 播放 {_num(s.get('views'))} · 赞 {_num(s.get('likes'))} · 评 {_num(s.get('comments'))} · 藏 {_num(s.get('saves'))}</span></td></tr>")
        return "".join(rows)

    hl = ""
    if highlights:
        items = "".join(
            f"<div style='background:#F3EAD3;border:1px solid #231C33;border-radius:12px;padding:8px 12px;margin:4px 0;font-size:14px;'>{i + 1}. <b>{h.get('title')}</b> <span style='color:#16BA5B'>▲+{_num(h.get('like_growth'))}</span></div>"
            for i, h in enumerate(highlights[:3]))
        hl = f"<h2 style='font-size:18px;margin:0 0 8px;'>⭐ 本周必看 Top 3</h2>{items}"

    unsub_link = unsubscribe_url or "#"
    return f"""<div style="background:#F9F7F5;padding:24px;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;color:#231C33;">
  <div style="max-width:640px;margin:0 auto;background:#FFFFFF;border:2px solid #231C33;border-radius:20px;overflow:hidden;">
    <div style="background:#231C33;color:#fff;padding:20px 24px;">
      <div style="font-size:22px;font-weight:700;">📡 弹幕雷达 <span style="color:#F5D652;">Danmaku Radar</span></div>
      <div style="font-size:13px;color:#B9B4C4;">{week} · B站真实热榜 + 百度热搜 + 弹幕热词</div>
    </div>
    <div style="padding:20px 24px;">
      {hl}
      <h2 style="font-size:18px;margin:14px 0 10px;">🔥 内容热榜 Top 20</h2>
      <table style="width:100%;border-collapse:collapse;">{post_rows(posts)}</table>
      <p style="font-size:12px;color:#736C83;">完整 Top 20 与评论总结见网站。</p>
      <h2 style="font-size:18px;margin:18px 0 8px;">🏷️ 话题热榜 Top 20</h2>
      <div style="line-height:2;">{_chip_spans([f"{t.get('topic')} ▲{t.get('post_growth')}" for t in topics], "#EAE8FE")}</div>
      <h2 style="font-size:18px;margin:18px 0 8px;">💬 弹幕热词</h2>
      <div style="line-height:2;">{_chip_spans([f"{w.get('word')}×{w.get('count')}" for w in danmaku or []], "#D8F9F0")}</div>
      <h2 style="font-size:18px;margin:18px 0 8px;">🔥 百度热搜</h2>
      <div style="line-height:2;">{_chip_spans([h.get('word') for h in hot or []], "#FEF2ED")}</div>
      <div style="margin-top:20px;padding-top:14px;border-top:1px solid #EEE;font-size:12px;color:#736C83;">
        免费订阅 · 每周一推送 · <a href="{unsub_link}" style="color:#5522FA;">点此退订</a>
      </div>
    </div>
  </div>
</div>"""
