/* 弹幕雷达 Danmaku Radar · HEY 风格完整落地页 */
'use strict';
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let toastTimer = null;
function toast(msg) { const t = $('#toast'); t.textContent = msg; t.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 2400); }
const FAV_KEY = 'dm_favs';
function ic(name, cls) { return '<svg class="ic ' + (cls || '') + '"><use href="#i-' + name + '"/></svg>'; }
const BACKEND = (window.DANMAKU_API && String(window.DANMAKU_API).trim()) || 'http://127.0.0.1:8000';
async function fetchWithTimeout(url, ms = 8000) {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), ms);
  try { return await fetch(url, { cache: 'no-store', signal: ctl.signal }); }
  finally { clearTimeout(t); }
}

const STOP = new Set('的了是就在和与及或不把被为有这那也都还要我们你们他们一个可以因为所以但是然后进行通过对于'.split(''));

const FALLBACK = {
  week: '2026-08-11 ~ 2026-08-17', generated_at: '2026-08-17T08:00:00+08:00', platform: 'bilibili',
  content_rank: [{ rank: 1, title: '【年度盘点】2026 年必看的 10 部动画，最后一集直接封神', author: '二次元观察社', category: '动画', url: '#', topics: ['#动画', '#年度盘点'], stats: { likes: 156000, like_growth: 62000, comments: 4800, saves: 23000 }, comment_summary: '评论区大量「泪目」「封神」，很多人在求完整片单。', summary: '盘点 2026 年最值得看的动画，细节拉满。', published_at: '2026-08-16' }],
  topic_rank: [{ rank: 1, topic: '#B站年度报告', post_count: 8600, post_growth: 2100, trend: '+32%' }]
};
const state = { data: null, favs: [], filter: '全部' };

async function loadStatic() {
  const urls = ['../data/latest.json', 'data/latest.json', 'examples/demo-posts.json'];
  for (const u of urls) {
    try { const r = await fetchWithTimeout(u, 3000); if (r.ok) { state.data = await r.json(); state.fromBackend = false; return true; } } catch (e) { /* next */ }
  }
  state.data = FALLBACK; state.fromBackend = false; return false;
}
async function loadBackend() {
  try {
    const r = await fetchWithTimeout(BACKEND + '/api/trends', 4000);
    if (r.ok) {
      const j = await r.json();
      if (j && Array.isArray(j.content_rank) && j.content_rank.length) {
        state.data = j; state.fromBackend = true;
        renderTrends(); renderFavs();
      }
    }
  } catch (e) { /* 后端未连接，保持静态数据 */ }
}
async function loadData() {
  await loadStatic();
  loadBackend();
}
function allPosts() { return state.data.content_rank || []; }

function extractKeywords(text, n) {
  const runs = String(text || '').match(/[\u4e00-\u9fff]{2,4}/g) || [];
  const freq = {};
  for (const g of runs) { if (STOP.has(g) || g.length < 2) continue; freq[g] = (freq[g] || 0) + 1; }
  return Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, n || 6).map(e => e[0]);
}
function parseTags(s) { return String(s || '').split(/[\s,，、]+/).map(t => t.trim()).filter(Boolean).slice(0, 12); }
function titlePatterns(t) {
  const out = [];
  if (/^\d/.test(t)) out.push('数字开头（清单 / 步骤感）');
  if (/[？?]/.test(t)) out.push('疑问句（引发好奇）');
  if (/[！!]/.test(t)) out.push('感叹 / 强情绪词');
  if (/别再|必看|神器|居然|亲测|保姆级|从0到1|避坑|我靠/.test(t)) out.push('高传播关键词');
  if (!out.length) out.push('平实陈述');
  return out;
}

// ---------- 热榜 ----------
function renderTrends() {
  if (!state.data) return;
  const posts = allPosts();
  const hot = state.data.hot_search || [];
  const fetchTime = state.data.last_fetch || state.data.generated_at || '-';
  $('#trends-week').textContent = '周范围 ' + (state.data.week || '-') + ' · 平台 ' + (state.data.platform || '-') + ' · 排序口径：近 7 天点赞增量 · 数据更新于 ' + fetchTime;
  const badge = $('#data-badge');
  if (state.fromBackend) {
    badge.textContent = '真实数据 · B站 · 更新于 ' + fetchTime;
    badge.style.display = '';
    badge.classList.add('ok');
  } else {
    badge.textContent = '';
    badge.style.display = 'none';
    badge.classList.remove('ok');
  }
  // 分类筛选
  const cats = ['全部'].concat(Array.from(new Set(posts.map(p => p.category).filter(Boolean))));
  const chips = cats.map(c => '<button class="chip' + (state.filter === c ? ' active' : '') + '" data-cat="' + esc(c) + '">' + esc(c) + '</button>').join('');
  $('#trends-filter').innerHTML = chips;
  $$('#trends-filter .chip').forEach(b => b.addEventListener('click', () => {
    state.filter = b.dataset.cat;
    renderTrendsList();
    $$('#trends-filter .chip').forEach(x => x.classList.toggle('active', x === b));
  }));
  renderTrendsList();
  const marq = hot.length ? hot.map(h => h.word) : (state.data.danmaku_words || []).map(w => w.word);
  $('#marquee').innerHTML = marq.concat(marq).map(w => '<a class="marquee-item" href="https://search.bilibili.com/all?keyword=' + encodeURIComponent(w) + '" target="_blank" rel="noopener">' + esc(w) + '</a>').join('');
  renderHotSearch();
  renderHighlights();
}
function renderTrendsList() {
  const list = state.filter === '全部' ? allPosts() : allPosts().filter(p => p.category === state.filter);
  if (!list.length) {
    $('#trends-list').innerHTML = '<div class="empty">暂无数据：请先启动后端并执行 <b>python backend/refresh.py</b> 抓取真实数据。</div>';
    return;
  }
  $('#trends-list').innerHTML = list.map(postCard).join('');
  $$('#trends-list [data-act]').forEach(b => b.addEventListener('click', onPostAction));
}
function fmtDur(sec) {
  sec = Number(sec) || 0;
  if (sec <= 0) return '';
  const m = Math.floor(sec / 60), s2 = sec % 60;
  return m + ':' + String(s2).padStart(2, '0');
}
function postCard(p) {
  const s = p.stats || {};
  const dm = p.danmaku_words || [];
  const cmts = p.top_comments || [];
  const fans = p.author_fans ? ('粉丝 ' + Number(p.author_fans).toLocaleString() + ' · Lv.' + (p.author_level || '-') + ' · 投稿 ' + (p.author_archives || '-')) : '';
  const dur = fmtDur(p.duration);
  const meta = [esc(p.author), esc(p.category || ''), esc(p.published_at || '')].filter(Boolean);
  if (dur) meta.push('时长 ' + dur);
  const link = p.url && p.url !== '#' ? p.url : '';
  const pic = String(p.pic || '').replace(/^http:\/\//i, 'https://');
  return '<div class="post-card">'
    + '<div class="post-top"><span class="rank-badge' + (Number(p.rank) <= 3 ? ' rb-' + Number(p.rank) : '') + '">' + (p.rank || '') + '</span>'
    + (p.pic && link ? '<a class="thumb" href="' + esc(link) + '" target="_blank" rel="noopener" tabindex="-1" aria-hidden="true" referrerpolicy="no-referrer"><img src="' + esc(pic) + '" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.display=\'none\';this.parentNode.classList.add(\'thumb-fallback\')"><span class="thumb-ph">' + esc(p.category || 'B站') + '</span></a>' : '')
    + '<div class="post-main">'
    + (link ? '<a class="post-title" href="' + esc(link) + '" target="_blank" rel="noopener">' + esc(p.title) + '</a>' : '<h3 class="post-title">' + esc(p.title) + '</h3>')
    + '<div class="post-meta">' + meta.join('<span class="dot-sep">·</span>') + (fans ? '<span class="dot-sep">·</span>' + fans : '') + '</div>'
    + '</div></div>'
    + '<div class="tags">' + (p.topics || []).map(t => '<span class="tag">' + esc(t) + '</span>').join('') + '</div>'
    + '<div class="stats">'
    + '<span class="st">' + ic('eye') + (s.views || 0).toLocaleString() + '</span>'
    + '<span class="st">' + ic('heart') + (s.likes || 0).toLocaleString() + '</span>'
    + '<span class="st growth">' + ic('bolt') + '本周 +' + (s.like_growth || 0).toLocaleString() + '</span>'
    + '<span class="st">' + ic('chat') + (s.comments || 0).toLocaleString() + '</span>'
    + '<span class="st">' + ic('star') + (s.saves || 0).toLocaleString() + '</span>'
    + '</div>'
    + (p.summary ? '<div class="ai-summary">' + ic('pen') + '<span class="ai-label">这条视频讲了什么</span><p>' + esc(p.summary) + '</p></div>' : '')
    + (dm.length ? '<div class="dm-box"><span class="dm-label">' + ic('chat') + ' 本视频弹幕热词</span>' + dm.map(w => '<span class="tag hot">' + esc(w.word) + ' <i>×' + (w.count || 0) + '</i></span>').join('') + '</div>' : '')
    + (cmts.length ? '<details class="cmt-details"><summary>' + ic('chat') + ' 评论区 TOP' + cmts.length + '（共 ' + (s.comments || 0) + ' 条）<span class="chev">' + ic('chev') + '</span></summary><ul class="cmt-list">'
        + cmts.map(c => '<li><b>' + esc(c.user) + '</b> <span class="cmt-likes">' + ic('bolt') + (c.likes || 0) + '</span><div>' + esc(c.content) + '</div></li>').join('')
        + '</ul></details>' : '')
    + '<div class="btn-row">'
    + (p.url && p.url !== '#' ? '<a class="btn small" href="' + esc(p.url) + '" target="_blank" rel="noopener">直达原帖 ' + ic('ext') + '</a>' : '')
    + '<button class="btn small" data-act="download" data-id="' + (p.rank || '') + '">' + ic('down') + ' 下载</button>'
    + '<button class="btn small" data-act="learnsearch" data-id="' + (p.rank || '') + '">' + ic('search') + ' 同类学习</button>'
    + '<button class="btn primary small" data-act="learn" data-id="' + (p.rank || '') + '">' + ic('pen') + ' 拆解</button>'
    + '<button class="btn small" data-act="clone" data-id="' + (p.rank || '') + '">' + ic('copy') + ' 克隆</button>'
    + '<button class="btn ghost small" data-act="favpost" data-id="' + (p.rank || '') + '">' + ic('star') + ' 收藏</button>'
    + '<button class="btn ghost small" data-copy="' + esc(p.title + ' ' + (p.url || '')) + '">' + ic('copy') + ' 复制</button>'
    + '</div></div>';
}
function renderHighlights() {
  const box = document.getElementById('highlights');
  if (!box) return;
  const hl = state.data.highlights || [];
  if (!hl.length) { box.innerHTML = ''; return; }
  box.innerHTML = hl.map(h =>
    '<div class="hl-card"><b>' + esc(h.title) + '</b>'
    + '<span class="hl-growth">' + ic('bolt') + ' 本周 +' + (h.like_growth || 0).toLocaleString() + '</span>'
    + '<span class="hl-meta">' + esc(h.category || '') + ' · ' + esc(h.author || '') + '</span>'
    + '<div class="btn-row"><a class="btn small" href="' + esc(h.url || '#') + '" target="_blank" rel="noopener">直达 ' + ic('ext') + '</a>'
    + '<button class="btn ghost small" data-copy="' + esc(h.title) + '">复制标题</button></div></div>'
  ).join('');
}
function renderHotSearch() {
  const hot = state.data.hot_search || [];
  const box = document.getElementById('hot-search');
  if (!box) return;
  if (!hot.length) { box.innerHTML = '<span class="hint">本次未取到百度热搜</span>'; return; }
  box.innerHTML = hot.map((h, i) =>
    '<a class="hot-chip" href="' + esc(h.url || '#') + '" target="_blank" rel="noopener">'
    + '<b>' + (h.rank || i + 1) + '</b> ' + esc(h.word) + '</a>'
  ).join('');
}
function findPost(rank) { return allPosts().find(p => Number(p.rank) === Number(rank)); }
function onPostAction(e) {
  const p = findPost(e.target.dataset.id);
  if (!p) return;
  state.curPost = p;
  const content = p.summary || p.comment_summary || '';
  if (e.target.dataset.act === 'learn') {
    $('#learn-title').value = p.title; $('#learn-content').value = content; $('#learn-tags').value = (p.topics || []).join(' ');
    document.getElementById('learn').scrollIntoView({ behavior: 'smooth' });
    toast('已填入爆款，点「开始拆解」');
  }
  if (e.target.dataset.act === 'clone') {
    $('#clone-title').value = p.title; $('#clone-content').value = content; $('#clone-tags').value = (p.topics || []).join(' ');
    document.getElementById('clone').scrollIntoView({ behavior: 'smooth' });
    toast('已填入爆款，点「生成完整脚本」');
  }
  if (e.target.dataset.act === 'favpost') { addFav('爆款', p.title, '作者 ' + p.author + ' ｜ ▲' + ((p.stats && p.stats.like_growth) || 0) + ' 赞 ｜ ' + (p.url || '')); toast('已收藏'); }
  if (e.target.dataset.act === 'download') { openDownloadModal(p); }
  if (e.target.dataset.act === 'learnsearch') { openLearnModal(p); }
}

// ---------- 下载源视频 & 跨平台同类学习 ----------
const PLATFORMS = [
  { name: 'B站', icon: 'play', url: (k) => 'https://search.bilibili.com/all?keyword=' + encodeURIComponent(k) },
  { name: 'YouTube', icon: 'play', url: (k) => 'https://www.youtube.com/results?search_query=' + encodeURIComponent(k) },
  { name: '抖音', icon: 'play', url: (k) => 'https://www.douyin.com/search/' + encodeURIComponent(k) },
  { name: '小红书', icon: 'book', url: (k) => 'https://www.xiaohongshu.com/search_result?keyword=' + encodeURIComponent(k) },
  { name: '快手', icon: 'play', url: (k) => 'https://www.kuaishou.com/search/video?searchKey=' + encodeURIComponent(k) },
  { name: '微博', icon: 'chat', url: (k) => 'https://s.weibo.com/weibo?q=' + encodeURIComponent(k) },
  { name: 'X / Twitter', icon: 'eye', url: (k) => 'https://x.com/search?q=' + encodeURIComponent(k) },
  { name: 'Reddit', icon: 'chat', url: (k) => 'https://www.reddit.com/search/?q=' + encodeURIComponent(k) }
];
function renderPlatformLinks(keyword) {
  const k = String(keyword || '').trim();
  if (!k) return '<span class="hint">请先输入关键词。</span>';
  return PLATFORMS.map(p =>
    '<a class="platform-link" href="' + p.url(k) + '" target="_blank" rel="noopener">' + ic(p.icon) + '<span>' + esc(p.name) + '</span></a>'
  ).join('');
}
function openModal(id) { const m = document.getElementById(id); if (m) m.classList.add('open'); }
function closeModal(id) { const m = document.getElementById(id); if (m) m.classList.remove('open'); }
function closeAllModals() { $('.modal.open').forEach(m => m.classList.remove('open')); }
function extractBvid(post) {
  const u = post.url || '';
  const m = String(u).match(/BV[0-9A-Za-z]{10}/);
  return m ? m[0] : (post.bvid || '');
}
function openDownloadModal(post) {
  const body = $('#download-body');
  if (!body) return;
  const url = post.url && post.url !== '#' ? post.url : '';
  const bvid = extractBvid(post);
  let h = '<div class="dl-title">' + esc(post.title) + '</div>';
  h += '<div class="dl-origin">'
    + (url ? '<a class="btn small" href="' + esc(url) + '" target="_blank" rel="noopener">' + ic('ext') + ' 打开原视频</a>' : '')
    + (bvid ? '<button class="btn small" data-copy="' + esc(bvid) + '">' + ic('copy') + ' 复制 BV 号</button>' : '')
    + (url ? '<button class="btn small" data-copy="' + esc(url) + '">' + ic('copy') + ' 复制链接</button>' : '')
    + '</div>';
  h += '<div class="dl-steps"><h4>下载方式</h4><ol>'
    + '<li>点击「打开原视频」，在浏览器或 B站客户端中确认视频可正常播放。</li>'
    + '<li>手机端：B站 App 支持「缓存」到本地，离线也能看。</li>'
    + '<li>电脑端：可选用 yt-dlp 等开源工具，命令：<code>yt-dlp "视频链接"</code></li>'
    + '<li>下载内容仅供个人学习与研究，请勿用于商业用途。</li>'
    + '</ol></div>';
  h += '<p class="dl-note">' + ic('book') + ' 本项目只提供入口与指引，不托管任何视频文件。</p>';
  body.innerHTML = h;
  openModal('download-modal');
}
function openLearnModal(post) {
  const body = $('#learn-body');
  if (!body) return;
  const k = String(post.title || '').replace(/^[#\s]+/, '').trim();
  let h = '<div class="dl-title">' + esc(post.title) + '</div>';
  h += '<p class="hint">已按标题关键词，在 8 个平台生成同类视频搜索入口，点击即可对照学习选题、结构、剪辑与文案。</p>';
  h += '<div class="lab-links">' + renderPlatformLinks(k) + '</div>';
  body.innerHTML = h;
  openModal('learn-modal');
}

// ---------- Learn ----------
function bdSec(title, body, icon) { return '<div class="bd-sec"><h4>' + (icon ? ic(icon) : '') + title + '</h4><div>' + body + '</div></div>'; }
function kpiLine(k, v) { return '<span class="bd-kpi"><b>' + (Number(v) || 0).toLocaleString() + '</b>' + esc(k) + '</span>'; }
function analyzePost(title, content, tags, post) {
  const t = title || '', c = content || '';
  const kws = extractKeywords(t + ' ' + c, 6);
  const stats = (post && post.stats) || null;
  const views = stats ? stats.views || 0 : 0;
  const likes = stats ? stats.likes || 0 : 0;
  const comments = stats ? stats.comments || 0 : 0;
  const saves = stats ? stats.saves || 0 : 0;
  const growth = stats ? stats.like_growth || 0 : 0;
  const danmaku = (post && post.danmaku_words) || [];
  const cmts = (post && post.top_comments) || [];
  const dur = Number((post && post.duration) || 0);
  const cat = (post && post.category) || '';
  const author = post ? post.author : '';
  const fans = Number((post && post.author_fans) || 0);
  const level = (post && post.author_level) || 0;
  const archives = (post && post.author_archives) || 0;
  const sign = (post && post.author_sign) || '';
  const published = (post && post.published_at) || '';
  const likeRate = views ? (likes / views * 100) : 0;
  const saveRate = likes ? (saves / likes * 100) : 0;
  const cmtRate = likes ? (comments / likes * 100) : 0;
  const engRate = views ? ((likes + saves * 2 + comments * 3) / views * 100) : 0;

  let edit = '';
  if (dur <= 0) edit = '时长未知：建议前 3 秒给到最强钩子，全程保持信息密度';
  else if (dur < 60) edit = '短平快（' + dur + ' 秒）：适合信息流快节奏，单点爆梗+强反转，建议卡点剪辑、无废话';
  else if (dur < 180) edit = '中视频（' + fmtDur(dur) + '）：前 3 秒钩子 → 每 20-30 秒一个小爆点 → 结尾升华或引导';
  else edit = '长视频（' + fmtDur(dur) + '）：深度内容，建议章节化：钩子 → 展开 → 高潮 → 总结，可加章节标题与进度提示';

  const styleMap = {
    '搞笑': '快节奏剪辑+夸张表情/音效+大字弹幕风字幕，转场利落',
    '音乐': '卡点混剪+歌词字幕，转场干净，色调统一',
    '动画': '高能片段剪辑+术语字幕，节奏跟随BGM',
    '知识': '信息密度高，图表+大字要点，画面留白，语速适中',
    '游戏': '高光集锦+名场面回放，镜头切换快，配合解说',
    '美食': '特写+步骤分镜，暖色调，音效突出',
    '日常': '第一视角+生活流，真实感优先，轻快BGM'
  };
  const style = styleMap[cat] || '建议：画面简洁、字幕清晰、色彩统一，前 3 秒放最强画面';

  let cmtTrend = '暂无热评数据';
  if (cmts.length) {
    const praise = cmts.filter(x => /好|牛|绝|神|泪|燃|可爱|快乐|开心|厉害|喜欢/.test(x.content)).length;
    const ask = cmts.filter(x => /求|哪里|怎么|多少|链接|教程|歌名|BGM/.test(x.content)).length;
    const parts = [];
    if (praise >= Math.ceil(cmts.length / 2)) parts.push('情绪共鸣强（好评/泪目/燃）');
    if (ask) parts.push(ask + ' 条在追问细节（求教程/求BGM/求链接）');
    if (cmts.some(x => /[?？]/.test(x.content))) parts.push('热评含提问，互动讨论度高');
    cmtTrend = parts.length ? parts.join('；') : '整体讨论积极';
  }

  let acct = '';
  if (fans >= 1000000) acct = '头部账号（粉丝 ' + (fans / 10000).toFixed(0) + ' 万+）：自带流量池，内容偏人设与品牌';
  else if (fans >= 100000) acct = '腰部账号（粉丝 ' + (fans / 10000).toFixed(0) + ' 万）：内容与运营并重，选题可复制性更强';
  else if (fans >= 10000) acct = '新锐账号（粉丝 ' + (fans / 10000).toFixed(1) + ' 万）：强内容驱动，这套打法可借鉴度高';
  else acct = fans ? ('成长型账号（粉丝 ' + fans.toLocaleString() + '）：靠单条爆款破圈，选题红利明显') : '账号数据未知';

  const summary = '「' + t + '」属于「' + (cat || '综合') + '」赛道：'
    + (views ? '播放 ' + views.toLocaleString() + '，' : '')
    + (likes ? '点赞 ' + likes.toLocaleString() + '（点赞率 ' + likeRate.toFixed(1) + '%），' : '')
    + '本周新增赞 ' + growth.toLocaleString() + '；'
    + '收藏/赞 ' + saveRate.toFixed(0) + '%、评论/赞 ' + cmtRate.toFixed(0) + '%；'
    + acct + '；' + edit;

  return { title: t, cat: cat, kws: kws, tags: parseTags(tags), stats: { views: views, likes: likes, comments: comments, saves: saves, growth: growth, likeRate: likeRate, saveRate: saveRate, cmtRate: cmtRate, engRate: engRate }, danmaku: danmaku, cmts: cmts, dur: dur, edit: edit, style: style, cmtTrend: cmtTrend, acct: acct, author: author, fans: fans, level: level, archives: archives, sign: sign, published: published, summary: summary };
}
function renderBreakdown(r) {
  const st = r.stats;
  const dm = r.danmaku.slice(0, 8);
  return '<div class="card reveal in" style="max-width:1160px;margin:26px auto;padding-left:28px;padding-right:28px;"><h2>爆款拆解卡</h2>'
    + '<p class="bd-summary"><b>一句话总结：</b>' + esc(r.summary) + '</p>'
    + '<div class="bd-grid">'
    + bdSec('热度诊断', kpiLine('播放', st.views) + kpiLine('点赞', st.likes) + kpiLine('本周新增赞', st.growth) + kpiLine('评论', st.comments) + kpiLine('收藏', st.saves)
        + '<p>点赞率 ' + st.likeRate.toFixed(1) + '% ｜ 收藏/赞 ' + st.saveRate.toFixed(1) + '% ｜ 评论/赞 ' + st.cmtRate.toFixed(1) + '% ｜ 综合互动率 ' + st.engRate.toFixed(1) + '%</p>', 'fire')
    + bdSec('内容与选题', '赛道：' + esc(r.cat || '综合') + '；核心关键词：' + r.kws.map(k => '<span class="tag">' + esc(k) + '</span>').join('')
        + '；标签：' + (r.tags.length ? r.tags.map(t => '<span class="tag alt">' + esc(t) + '</span>').join('') : '<span class="hint">无</span>'), 'tag')
    + bdSec('剪辑与节奏', esc(r.edit), 'pen')
    + bdSec('画面风格', esc(r.style), 'eye')
    + bdSec('技术/专业热词', dm.length ? dm.map(w => '<span class="tag hot">' + esc(w.word) + ' ×' + w.count + '</span>').join('') : '<span class="hint">暂无弹幕热词</span>', 'bolt')
    + bdSec('评论区风向', esc(r.cmtTrend) + (r.cmts.length ? '<ul class="cmt-list">' + r.cmts.slice(0, 3).map(c => '<li><b>' + esc(c.user) + '</b> <span class="cmt-likes">' + ic('bolt') + (c.likes || 0) + '</span><div>' + esc(c.content) + '</div></li>').join('') + '</ul>' : ''), 'chat')
    + bdSec('作者与账号', esc(r.acct) + (r.level ? '；账号等级 Lv.' + r.level : '') + (r.archives ? '；累计投稿 ' + r.archives + ' 条' : '') + (r.sign ? '；签名：' + esc(r.sign) : '') + (r.published ? '；发布时间：' + esc(r.published) : ''), 'star')
    + bdSec('发布因素', (r.published ? '发布于 ' + esc(r.published) : '发布时间未知') + '；本周新增赞 ' + st.growth.toLocaleString() + '，爆发力' + (st.growth > 100000 ? '极强（>10万）' : st.growth > 30000 ? '强（3万+）' : st.growth > 5000 ? '中等（5千+）' : '一般') + '；' + esc(r.acct), 'chart')
    + '</div>'
    + '<div class="btn-row"><button id="btn-save-breakdown" class="btn primary">' + ic('star') + ' 收藏这张拆解卡</button><button class="btn ghost" data-copy="' + esc(r.summary) + '">' + ic('copy') + ' 复制文案</button></div></div>';
}

// ---------- Clone ----------
function generateScript(title, post) {
  const t = title || '';
  const cat = (post && post.category) || '综合';
  const kws = extractKeywords(t, 5);
  const base = kws[0] || '这个主题';
  const tags = (post && post.topics) || [];
  const dm = (post && post.danmaku_words) || [];
  const cmts = (post && post.top_comments) || [];
  const dur = Number((post && post.duration) || 0);
  const author = (post && post.author) || '';
  const fans = Number((post && post.author_fans) || 0);
  const level = (post && post.author_level) || 0;
  const archives = (post && post.author_archives) || 0;
  const sign = (post && post.author_sign) || '';
  const stats = (post && post.stats) || {};
  const dmHook = dm[0] ? dm[0].word : base;
  const cmtHook = cmts[0] ? cmts[0].content.slice(0, 24) : '评论区都在问';
  const titles = [
    '别再' + base + '了！这样做才是对的（亲测）',
    '我发现' + base + '的真相，90%的人都搞错了',
    '从0到1搞定' + base + '：新手保姆级教程',
    '如果只能推荐一个' + base + '，我选它'
  ];
  const outline = [
    '开场 0-3 秒：直接抛出最强钩子。参考原爆款「' + (t.slice(0, 20) || base) + '」的抓人方式，换成你版本的第一句爆点',
    '第 3-10 秒：点明「这条视频能给你什么」（情绪价值 / 干货 / 爽点）。弹幕热词「' + dmHook + '」可做成口头禅或字幕关键词',
    '中段 60%：安排 3 个递进小爆点（原视频节奏参考：' + (dur ? fmtDur(dur) + '，每 20-30 秒一个记忆点' : '每 20-30 秒一个记忆点') + '）',
    '后段：回应评论区最关心的问题（例如「' + cmtHook + '…」），把观众的问题直接做成内容',
    '结尾：引导点赞/投币/收藏 + 关注，并埋一个「下期预告」钩子'
  ];
  const edit = '剪辑方案：' + (dur <= 0 ? '建议时长控制在 60-120 秒' : dur < 60 ? '快节奏卡点（' + dur + ' 秒版），每个镜头不超过 3 秒' : dur < 180 ? '分段推进：3 秒钩子 → 3 个爆点 → 结尾升华（约 ' + fmtDur(dur) + '）' : '章节化长视频：开场钩子 + 章节标题 + 高潮 + 总结（约 ' + fmtDur(dur) + '）')
    + '；字幕加粗大字+关键词变色；转场用硬切/缩放，不用花哨特效；关键画面加「弹幕热词」角标强化记忆点';
  const music = '配乐：前 3 秒用强节奏BGM卡点，中段换轻快BGM，高潮段叠音效；建议参考同类「' + cat + '」爆款的BGM风格';
  const cover = '封面：大字标题 + 主角情绪脸/最强画面 + 一个悬念词；标题文案从上面 4 个方案里选，前 16 字放核心信息';
  const publish = '发布：选择目标人群活跃时段（学生党晚 18-22 点、职场人午休/通勤）；标题带 ' + (tags.length ? tags.slice(0, 3).join(' ') : ('#' + base)) + ' 等话题标签；发布后 1 小时内回复热评并置顶一条引导评论';
  const acct = (author ? '参考账号「' + author + '」' : '参考账号') + (fans ? '（粉丝 ' + fans.toLocaleString() + (level ? '，Lv.' + level : '') + (archives ? '，投稿 ' + archives + ' 条' : '') + '）' : '')
    + '：' + (fans >= 1000000 ? '该账号靠人设+稳定更新起量，你的克隆应突出「真实身份+持续更新」' : fans >= 100000 ? '该账号选题复用度高，你的克隆应聚焦同一赛道连续做 3 期' : '该账号靠单条爆款破圈，你的克隆应把这条的选题红利吃透，尽快发布')
    + (sign ? '；账号签名：' + sign : '');
  const scriptText = '【完整克隆脚本】\n'
    + '一、选题定位：' + base + '（原爆款来自「' + cat + '」赛道）\n'
    + '二、差异化角度：把原爆款的爽点换成你的真实故事/专业视角/本地场景\n'
    + '三、标题方案（4选1）：\n' + titles.map((x, i) => '  ' + (i + 1) + '. ' + x).join('\n') + '\n'
    + '四、文案脚本：\n' + outline.map((x, i) => '  ' + (i + 1) + '. ' + x).join('\n') + '\n'
    + '五、' + edit + '\n'
    + '六、' + music + '\n'
    + '七、' + cover + '\n'
    + '八、' + publish + '\n'
    + '九、' + acct;
  return { titles: titles, angle: '差异化：' + base + ' × 你的真实故事/专业视角/本地场景', outline: outline, cat: cat, tags: tags, edit: edit, music: music, cover: cover, publish: publish, acct: acct, scriptText: scriptText };
}
function renderScript(s) {
  return '<div class="bd-grid">'
    + bdSec('选题定位', '赛道：' + esc(s.cat) + '；' + esc(s.angle), 'tag')
    + bdSec('标题方案（4 选 1）', s.titles.map((x, i) => '<p class="script-title">' + (i + 1) + '. ' + esc(x) + '</p>').join(''), 'pen')
    + bdSec('文案脚本（分镜大纲）', '<ol class="script-list">' + s.outline.map(x => '<li>' + esc(x) + '</li>').join('') + '</ol>', 'book')
    + bdSec('剪辑与制作', esc(s.edit) + '<br>' + esc(s.music) + '<br>' + esc(s.cover), 'copy')
    + bdSec('发布策略', esc(s.publish), 'bolt')
    + bdSec('账号建议（结合原作者）', esc(s.acct), 'star')
    + '</div>'
    + '<div class="btn-row"><button class="btn primary" data-save-script>' + ic('star') + ' 收藏脚本</button><button class="btn ghost" data-copy="' + esc(s.scriptText) + '">' + ic('copy') + ' 复制完整脚本</button></div>';
}

// ---------- 收藏 ----------
function loadFavs() { try { state.favs = JSON.parse(localStorage.getItem(FAV_KEY)) || []; } catch (e) { state.favs = []; } }
function saveFavs() { localStorage.setItem(FAV_KEY, JSON.stringify(state.favs)); }
function addFav(type, title, detail) {
  state.favs.unshift({ type: type, title: title, detail: detail, date: new Date().toISOString().slice(0, 10) });
  saveFavs(); renderFavs();
}
function renderFavs() {
  const ul = $('#favs-list');
  if (!state.favs.length) { ul.innerHTML = '<li class="hint">还没有收藏，去热榜收藏一些吧。</li>'; return; }
  ul.innerHTML = state.favs.map((f, i) => '<li><span class="tag">' + esc(f.type) + '</span><b> ' + esc(f.title) + '</b>'
    + '<div class="hint">' + esc(f.detail) + ' ｜ ' + esc(f.date) + '</div>'
    + '<div class="btn-row"><button class="btn btn-coral small" data-del-fav="' + i + '">删除</button></div></li>').join('');
  $$('#favs-list [data-del-fav]').forEach(b => b.addEventListener('click', () => { state.favs.splice(Number(b.dataset.delFav), 1); saveFavs(); renderFavs(); toast('已删除'); }));
}

// ---------- 交互 ----------
function initReveal() {
  const els = $$('.reveal');
  if (!('IntersectionObserver' in window)) {
    els.forEach(el => el.classList.add('in'));
    return;
  }
  const io = new IntersectionObserver((entries) => {
    entries.forEach(en => { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } });
  }, { threshold: 0.1 });
  els.forEach(el => io.observe(el));
  // 兜底：3 秒后强制显示所有尚未显现的内容，避免任何区块因动画问题不可见
  setTimeout(() => {
    $$('.reveal:not(.in)').forEach(el => el.classList.add('in'));
  }, 3000);
}
function setCounts(pairs) {
  const els = $$('.stat b');
  els.forEach((el, i) => { el.dataset.target = pairs[i] ? pairs[i][1] : 0; });
  const io = new IntersectionObserver((entries) => {
    entries.forEach(en => {
      if (!en.isIntersecting) return;
      const el = en.target; const target = Number(el.dataset.target || 0); const t0 = performance.now(); const dur = 1200;
      const tick = (t) => { const p = Math.min(1, (t - t0) / dur); el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3))).toLocaleString(); if (p < 1) requestAnimationFrame(tick); };
      requestAnimationFrame(tick); io.unobserve(el);
    });
  }, { threshold: 0.4 });
  els.forEach(el => io.observe(el));
}
function initScrollspy() {
  const links = $$('.nav-link');
  const sections = ['why', 'trends', 'search-lab', 'hot', 'learn', 'clone', 'subscribe', 'faq'].map(id => document.getElementById(id));
  const io = new IntersectionObserver((entries) => {
    entries.forEach(en => {
      if (!en.isIntersecting) return;
      links.forEach(l => l.classList.toggle('active', l.getAttribute('href') === '#' + en.target.id));
    });
  }, { rootMargin: '-40% 0px -55% 0px' });
  sections.forEach(s => { if (s) io.observe(s); });
}
function initBackTop() {
  const btn = $('#back-top');
  window.addEventListener('scroll', () => { btn.hidden = window.scrollY < 400; }, { passive: true });
  btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
}

// ---------- 事件 ----------
function bindEvents() {
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-copy]');
    if (!btn) return;
    const text = btn.dataset.copy || '';
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => toast('已复制到剪贴板')).catch(() => toast('复制失败'));
    } else { toast('当前浏览器不支持复制'); }
  });
  $('#btn-theme').addEventListener('click', () => {
    const dark = document.body.classList.toggle('dark');
    localStorage.setItem('dm_theme', dark ? 'dark' : 'light');
    $('#btn-theme').innerHTML = dark ? ic('sun') : ic('moon');

  $('#btn-menu').addEventListener('click', () => {
    const open = $('#nav').classList.toggle('open');
    $('#btn-menu').setAttribute('aria-expanded', String(open));
    $('#btn-menu').setAttribute('aria-label', open ? '关闭菜单' : '打开菜单');
  });
  $$('.nav-link').forEach(a => a.addEventListener('click', () => {
    $('#nav').classList.remove('open');
    $('#btn-menu').setAttribute('aria-expanded', 'false');
    $('#btn-menu').setAttribute('aria-label', '打开菜单');
  }));
  });

  $('#btn-lab-go').addEventListener('click', () => {
    const k = $('#lab-keyword').value.trim();
    if (!k) { toast('请输入关键词'); $('#lab-keyword').focus(); return; }
    $('#lab-msg').textContent = '已为「' + k + '」生成 8 个平台的学习搜索入口：';
    $('#lab-links').innerHTML = renderPlatformLinks(k);
  });
  $('#lab-keyword').addEventListener('keydown', (e) => { if (e.key === 'Enter') $('#btn-lab-go').click(); });
  $$('.modal-close').forEach(b => b.addEventListener('click', () => { const m = b.closest('.modal'); if (m) m.classList.remove('open'); }));
  $$('.modal').forEach(m => m.addEventListener('click', (e) => { if (e.target === m) m.classList.remove('open'); }));
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeAllModals(); });
  $('#btn-subscribe').addEventListener('click', () => subscribe('sub-email', 'sub-msg'));
  $('#btn-subscribe2').addEventListener('click', () => subscribe('sub-email2', 'sub-msg2'));
  $('#btn-subscribe-top').addEventListener('click', () => { document.getElementById('subscribe').scrollIntoView({ behavior: 'smooth' }); setTimeout(() => $('#sub-email2').focus(), 500); });
  $('#btn-learn').addEventListener('click', () => {
    const r = analyzePost($('#learn-title').value, $('#learn-content').value, $('#learn-tags').value, state.curPost || null);
    $('#learn-result').innerHTML = renderBreakdown(r);
    $('#btn-save-breakdown').addEventListener('click', () => { addFav('拆解卡', $('#learn-title').value || '未命名爆款', r.summary); toast('拆解卡已收藏'); });
  });
  $('#btn-clone').addEventListener('click', () => {
    const scr = generateScript($('#clone-title').value, state.curPost || null);
    $('#clone-result').innerHTML = '<div class="card reveal in" style="max-width:1160px;margin:26px auto;padding-left:28px;padding-right:28px;"><h2>完整克隆脚本（基于原爆款 + 作者账号）</h2>' + renderScript(scr) + '</div>';
    const saveBtn = $('#clone-result [data-save-script]');
    if (saveBtn) saveBtn.addEventListener('click', () => { addFav('脚本', $('#clone-title').value || '克隆脚本', scr.scriptText); toast('脚本已收藏'); });
  });
  $('#btn-export-favs').addEventListener('click', () => {
    const blob = new Blob([JSON.stringify(state.favs, null, 2)], { type: 'application/json' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'danmaku-radar-favs.json'; a.click();
    toast('已导出');
  });
  $('#btn-clear-favs').addEventListener('click', () => { if (!confirm('确定清空收藏？')) return; state.favs = []; saveFavs(); renderFavs(); toast('已清空'); });
}
async function subscribe(emailId, msgId) {
  const email = $('#' + emailId).value.trim();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { toast('请输入正确的邮箱'); return; }
  try {
    const r = await fetch(BACKEND + '/api/subscribe', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email, lang: 'both', categories: ($('#sub-cat') ? $('#sub-cat').value : '') || '' })
    });
    const j = await r.json();
    if (j && j.ok) {
      $('#' + emailId).value = '';
      $('#' + msgId).textContent = '订阅成功！已写入数据库，每周一自动推送';
      toast('订阅成功');
      return;
    }
    toast(j && j.msg ? j.msg : '订阅失败');
    return;
  } catch (e) { /* 后端未启动：本地记录 */ }
  const subs = JSON.parse(localStorage.getItem('dm_subscribers') || '[]');
  if (subs.includes(email)) { toast('该邮箱已订阅'); return; }
  subs.push(email); localStorage.setItem('dm_subscribers', JSON.stringify(subs));
  $('#' + emailId).value = '';
  $('#' + msgId).textContent = '订阅成功（本地记录）！启动后端后可正式入库';
  toast('订阅成功');
}

function skeleton(n) {
  let h = '';
  for (let i = 0; i < n; i++) {
    h += '<div class="skel-card"><div class="skel-line w90"></div><div class="skel-line w60"></div><div class="skel-line w75"></div></div>';
  }
  return h;
}
(async function init() {
  loadFavs();
  bindEvents();
  initReveal();
  initScrollspy();
  initBackTop();
  const savedTheme = localStorage.getItem('dm_theme');
  if (savedTheme === 'dark') { document.body.classList.add('dark'); $('#btn-theme').innerHTML = ic('sun'); }
  if ('serviceWorker' in navigator) { navigator.serviceWorker.register('sw.js').catch(() => {}); }
  $('#trends-list').innerHTML = skeleton(6);
  try { await loadData(); } catch (e) { state.data = state.data || FALLBACK; }
  localStorage.setItem('dm_lastload', String(Date.now()));
  renderTrends();
  renderFavs();
  requestAnimationFrame(() => $$('.hero .reveal, .eyebrow').forEach(el => el.classList.add('in')));
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) return;
    const last = Number(localStorage.getItem('dm_lastload') || 0);
    if (Date.now() - last > 10 * 60 * 1000) {
      loadData().then(() => { localStorage.setItem('dm_lastload', String(Date.now())); renderTrends(); renderFavs(); });
    }
  });
})();
