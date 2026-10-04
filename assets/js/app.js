/* 学习资源站 — 纯静态前端 */
const $ = (s, r = document) => r.querySelector(s);
const esc = (s = '') => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const qs = k => new URLSearchParams(location.search).get(k);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

const state = { items: [], tax: {}, meta: {}, cat: 'all', sub: 'all' };
const track = (name, data) => { try { if (window.umami && typeof window.umami.track === 'function') window.umami.track(name, data); } catch (e) {} };

/* ---------- 收藏（纯本地 localStorage，无后端） ---------- */
const FAV_KEY = 'xx_favs';
const FAV_MAX = 200;
function readFavs() { try { const v = JSON.parse(localStorage.getItem(FAV_KEY) || '[]'); return Array.isArray(v) ? v : []; } catch (e) { return []; } }
function writeFavs(v) { try { localStorage.setItem(FAV_KEY, JSON.stringify(v)); } catch (e) {} }
const favs = readFavs();
const isFav = id => !!id && favs.some(f => f.id === id);
const favCount = () => favs.length;
function toggleFav(it) {
  if (!it || !it.id) return false;
  const i = favs.findIndex(f => f.id === it.id);
  if (i >= 0) { favs.splice(i, 1); writeFavs(favs); return false; }
  favs.unshift({ id: it.id, title: it.title || '', category: it.category || '', subcategory: it.subcategory || '', desc: it.desc || '', size: it.size || '', tags: it.tags || [], favAt: new Date().toISOString() });
  if (favs.length > FAV_MAX) favs.length = FAV_MAX;
  writeFavs(favs);
  return true;
}
function removeFav(id) { const i = favs.findIndex(f => f.id === id); if (i >= 0) { favs.splice(i, 1); writeFavs(favs); } }
function updateFavBtn(id) {
  const btn = document.getElementById('fav-btn'); if (!btn) return;
  const on = isFav(id);
  btn.classList.toggle('on', on);
  btn.innerHTML = `<span class="fav-star">${on ? '★' : '☆'}</span> ${on ? '已收藏' : '收藏'}`;
}
window.toggleFavClick = function (id) {
  const it = state.items.find(x => x.id === id);
  if (!it) return;
  const on = toggleFav(it);
  updateFavBtn(id);
  track((on ? 'fav:' : 'unfav:') + id);
};
window.removeFavClick = function (id) { removeFav(id); renderFavorites(); };

/* ---------- 公告弹窗（数据在 data/site.json） ---------- */
const ANN_KEY = 'xx-announcement-dismissed';
function localDateKey() { const n = new Date(), p = v => String(v).padStart(2, '0'); return `${n.getFullYear()}-${p(n.getMonth() + 1)}-${p(n.getDate())}`; }
function linkify(text) {
  const e = esc(text).replace(/(https?:\/\/[^\s<)】]+)/g, u => `<a href="${u}" target="_blank" rel="noopener">${u}</a>`);
  return e.replace(/\n/g, '<br>');
}
window.toggleAnn = function (i) {
  const body = document.getElementById('ann-body-' + i);
  const chev = document.getElementById('ann-chev-' + i);
  if (!body) return;
  const open = body.style.display !== 'none';
  body.style.display = open ? 'none' : '';
  if (chev) chev.textContent = open ? '▸' : '▾';
};
window.closeAnn = function () { const m = document.getElementById('ann-mask'); if (m) m.remove(); };
window.closeAnnToday = function () {
  try {
    const m = document.getElementById('ann-mask');
    if (m) localStorage.setItem(ANN_KEY, JSON.stringify({ version: m.dataset.version || '', date: localDateKey() }));
  } catch (e) {}
  closeAnn();
};
async function loadAnnouncement() {
  let site = null;
  try { const r = await fetch('data/site.json', { cache: 'no-store' }); if (r.ok) site = await r.json(); } catch (e) { return; }
  const a = site && site.announcementModal;
  if (!a || !a.enabled) return;
  const items = Array.isArray(a.items) ? a.items : [];
  if (!a.content && !items.length) return;
  const version = a.version || ((a.title || '') + ':' + (a.content || ''));
  try { const d = JSON.parse(localStorage.getItem(ANN_KEY) || 'null'); if (d && d.version === version && d.date === localDateKey()) return; } catch (e) {}
  const timeline = items.length ? `<div class="ann-timeline">${items.map((it, i) => `
    <div class="ann-tl${i === 0 ? ' latest' : ''}">
      <button type="button" class="ann-tl-head" aria-expanded="${i === 0}" onclick="toggleAnn(${i})">
        <span class="ann-tl-dot" aria-hidden="true"></span>
        <span class="ann-tl-main">
          <span class="ann-tl-top"><span class="ann-tl-date">${esc(it.date || '')}</span>${it.tag ? `<span class="ann-tl-tag">${esc(it.tag)}</span>` : ''}</span>
          <span class="ann-tl-title">${esc(it.title || '')}</span>
        </span>
        <span class="ann-tl-chev" id="ann-chev-${i}" aria-hidden="true">${i === 0 ? '▾' : '▸'}</span>
      </button>
      <div class="ann-tl-body" id="ann-body-${i}"${i === 0 ? '' : ' style="display:none"'}>${linkify(it.content || '')}</div>
    </div>`).join('')}</div>` : `<div class="ann-text">${linkify(a.content || '')}</div>`;
  const box = document.createElement('div');
  box.className = 'ann-mask';
  box.id = 'ann-mask';
  box.dataset.version = version;
  box.innerHTML = `<section class="ann" role="dialog" aria-modal="true" aria-labelledby="ann-title">
    <button class="ann-close" type="button" title="关闭" aria-label="关闭公告" onclick="closeAnn()">✕</button>
    <div class="ann-icon">📢</div>
    <p class="ann-eyebrow">XUEXI NOTICE</p>
    <h2 id="ann-title">${esc(a.title || '站点公告')}</h2>
    ${timeline}
    <div class="ann-actions">
      <button class="ann-btn ghost" type="button" onclick="closeAnnToday()">今日关闭</button>
      <button class="ann-btn primary" type="button" onclick="closeAnn()">关闭</button>
    </div>
  </section>`;
  box.addEventListener('click', e => { if (e.target === box) closeAnn(); });
  document.body.appendChild(box);
}

async function boot() {
  const [res, tax] = await Promise.all([
    fetch('data/resources.json', { cache: 'no-store' }).then(r => r.json()),
    fetch('data/taxonomy.json', { cache: 'no-store' }).then(r => r.json())
  ]);
  state.items = res.items || [];
  state.meta = res;
  state.tax = tax;

  $('#site-header').innerHTML = headerHTML();
  $('#site-footer').innerHTML = footerHTML();

  const page = document.body.dataset.page;
  if (page === 'home') { renderHome(); loadAnnouncement(); }
  else if (page === 'category') renderCategory();
  else if (page === 'search') renderSearch();
  else if (page === 'resource') renderResource();
  else if (page === 'favorites') renderFavorites();
  initSearch();
}

function headerHTML() {
  const page = document.body.dataset.page;
  const on = p => (page === p ? ' class="on"' : '');
  const navs = Object.entries(state.tax).map(([slug, c]) =>
    `<a href="category.html?c=${slug}"${on('category-' + slug)}>${esc(c.name)}</a>`).join('');
  return `<div class="wrap hd-inner">
    <a class="logo" href="index.html" aria-label="学习资料站首页">
      <span class="logo-mark" aria-hidden="true"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg></span>
      <span class="logo-text"><b>学习资料站</b><i>真题 · 中小学 · 办公素材</i></span>
    </a>
    <nav class="hd-nav"><a href="index.html"${on('home')}>首页</a>${navs}</nav>
    <form class="hd-search" onsubmit="location.href='search.html?q='+encodeURIComponent(this.q.value);return false">
      <input name="q" placeholder="搜高考数学真题、三年级语文…" value="${esc(qs('q') || '')}">
    </form>
    <a class="hd-fav" href="favorites.html" title="我的收藏" aria-label="我的收藏">
      <span class="hd-fav-star">⭐</span><span class="hd-fav-text">收藏</span>${favCount() ? `<b>${favCount()}</b>` : ''}
    </a>
  </div>`;
}

function footerHTML() {
  const y = new Date().getFullYear();
  return `<div class="wrap ft-inner">
    <div>© ${y} 学习资源站 · 数据每日更新</div>
    <div>
      <a href="about.html">关于本站</a> ·
      <a href="disclaimer.html">免责声明</a> ·
      <a href="sitemap.xml">站点地图</a>
    </div>
  </div>`;
}

function setMeta(title, desc, canonical) {
  document.title = title;
  if (desc) {
    let d = document.head.querySelector('meta[name=description]');
    if (!d) { d = document.createElement('meta'); d.setAttribute('name', 'description'); document.head.appendChild(d); }
    d.setAttribute('content', desc);
  }
  let c = document.head.querySelector('link[rel=canonical]');
  if (!c) { c = document.createElement('link'); c.rel = 'canonical'; document.head.appendChild(c); }
  c.href = canonical || location.origin + location.pathname + location.search;
}

function catName(c) { return (state.tax[c] && state.tax[c].name) || c; }
function subName(c, s) {
  const t = state.tax[c];
  if (!t) return s;
  const f = (t.subs || []).find(x => x.slug === s);
  return f ? f.name : s;
}
function iconOf(it) {
  const m = { exam: '📝', study: '📖', office: '💼' };
  return m[it.category] || '📦';
}
function findSubOf(cat, sub) {
  const t = state.tax[cat];
  return t && (t.subs || []).find(x => x.slug === sub);
}

function cardHTML(it) {
  const href = `resource.html?id=${encodeURIComponent(it.id)}`;
  const tags = (it.tags || []).slice(0, 3).map(t => `<span class="tag">#${esc(t)}</span>`).join('');
  const demo = it.demo ? '<span class="badge">示例</span>' : '';
  return `<a class="card" href="${href}">
    <div class="card-top">
      <div class="card-ico">${iconOf(it)}</div>
      <h3>${esc(it.title)} ${demo}${it.updatedAt === localDateKey() ? '<span class="badge badge-new">今日上新</span>' : ''}</h3>
    </div>
    <p class="card-desc">${esc(it.desc || '')}</p>
    <div class="tags">${tags}</div>
    <div class="card-foot">
      <span class="card-meta">${esc(catName(it.category))}${it.subcategory ? ' · ' + esc(subName(it.category, it.subcategory)) : ''}${it.size ? ' · ' + esc(it.size) : ''}</span>
      <span class="cta">转存 →</span>
    </div>
  </a>`;
}

function filterItems() {
  return state.items.filter(it => {
    if (state.cat !== 'all' && it.category !== state.cat) return false;
    if (state.sub !== 'all' && it.subcategory !== state.sub) return false;
    return true;
  });
}

function gridOf(items) {
  if (!items.length) return `<div class="empty">这里还没有资料，换个分类看看 👀</div>`;
  return `<div class="grid">${items.map(cardHTML).join('')}</div>`;
}

function chipsHTML() {
  let h = `<button class="chip${state.cat === 'all' ? ' on' : ''}" data-c="all" data-s="all">全部</button>`;
  for (const [slug, c] of Object.entries(state.tax)) {
    h += `<button class="chip${state.cat === slug ? ' on' : ''}" data-c="${slug}" data-s="all">${esc(c.name)}</button>`;
  }
  return `<div class="chips" id="chips">${h}</div><div class="chips" id="subchips"></div>`;
}

function bindChips() {
  $('#chips').onclick = e => {
    const b = e.target.closest('.chip'); if (!b) return;
    state.cat = b.dataset.c; state.sub = 'all';
    document.querySelectorAll('#chips .chip').forEach(x => x.classList.toggle('on', x === b));
    renderSubchips(); paint();
  };
}

function renderSubchips() {
  const box = $('#subchips');
  const t = state.tax[state.cat];
  if (!t || !t.subs) { box.innerHTML = ''; return; }
  box.innerHTML = `<button class="chip${state.sub === 'all' ? ' on' : ''}" data-s="all">全部${esc(t.name)}</button>` +
    t.subs.map(s => `<button class="chip${state.sub === s.slug ? ' on' : ''}" data-s="${s.slug}">${esc(s.name)}</button>`).join('');
  box.onclick = e => {
    const b = e.target.closest('.chip'); if (!b) return;
    state.sub = b.dataset.s;
    box.querySelectorAll('.chip').forEach(x => x.classList.toggle('on', x === b));
    paint();
  };
}

function paint() {
  $('#grid').innerHTML = gridOf(filterItems());
}

/* ---------- pages ---------- */
function renderHome() {
  setMeta('学习资料站 - 高考真题|中考真题|中小学试卷|办公PPT模板 夸克网盘资源',
    '免费夸克网盘学习资料：高考真题、中考真题、中小学试卷与知识点、PPT 办公模板，一键转存、永久有效。');
  const n = state.items.filter(x => !x.demo).length || state.items.length;
  const subs = Object.values(state.tax).reduce((a, c) => a + (c.subs ? c.subs.length : 0), 0);
  $('#main').innerHTML = `
  <section class="hero">
    <div class="wrap">
      <h1>考试真题 · 中小学 · <em>办公素材</em></h1>
      <p>高考/中考真题、中小学试卷与知识点、PPT 办公模板，一键转存到自己的夸克网盘，永久有效。</p>
      <form class="hero-search" onsubmit="location.href='search.html?q='+encodeURIComponent(this.q.value);return false">
        <input name="q" placeholder="搜高考数学真题、三年级语文、述职 PPT…">
        <button>搜索</button>
      </form>
      <div class="stats">
        <div><b>${n}</b><span>已收录资料</span></div>
        <div><b>${Object.keys(state.tax).length}</b><span>大类</span></div>
        <div><b>${subs}</b><span>细分方向</span></div>
        <div><b>${esc(state.meta.updatedAt || '—')}</b><span>最近更新</span></div>
      </div>
    </div>
  </section>
  <div class="wrap">
    <div class="sec-title">🔥 热门分类 <small>按 考试真题 / 中小学资料 / 办公素材 浏览</small></div>
    ${chipsHTML()}
    <div id="grid"></div>
    <div class="notice">📌 本站仅整理公开分享信息，资源版权归原作者所有；转存后请自行遵守夸克网盘规则。</div>
  </div>`;
  renderSubchips(); bindChips(); paint();
}

function renderCategory() {
  const c = qs('c') || 'all';
  const s = qs('s') || 'all';
  state.cat = state.tax[c] ? c : 'all';
  state.sub = 'all';
  const t = state.tax[state.cat];
  setMeta(`${t ? t.name : '全部资料'} - 学习资料站`, `${t ? (t.desc || t.name) : '全部资料'}｜夸克网盘资源免费转存。`);
  $('#main').innerHTML = `<div class="wrap">
    <div class="crumb"><a href="index.html">首页</a> / ${esc(t ? t.name : '全部')}</div>
    <div class="sec-title">${esc(t ? t.name : '全部资料')} <small>${esc(t ? (t.desc || '') : '')}</small></div>
    ${chipsHTML()}
    <div id="grid"></div>
  </div>`;
  renderSubchips();
  if (t && s !== 'all' && findSubOf(state.cat, s)) {
    state.sub = s;
    $$('#subchips .chip').forEach(x => x.classList.toggle('on', x.dataset.s === s));
  }
  bindChips(); paint();
}

function renderSearch() {
  const q = (qs('q') || '').trim();
  setMeta(`搜索「${q}」 - 学习资料站`, `在学习资料站搜索「${q}」的夸克网盘资源。`);
  const res = q ? searchItems(q) : { total: state.items.length, hits: state.items, tier: 'all' };
  const items = res.hits;
  const fuzzyNote = q && (res.tier === 'subsequence' || res.tier === 'typo')
    ? ' · 模糊匹配' : '';
  $('#main').innerHTML = `<div class="wrap">
    <div class="crumb"><a href="index.html">首页</a> / 搜索</div>
    <div class="sec-title">搜索「${esc(q)}」 <small>找到 ${items.length} 条${fuzzyNote}</small></div>
    ${gridOf(items)}
  </div>`;
}

function renderResource() {
  const id = qs('id');
  const it = state.items.find(x => x.id === id);
  if (!it) {
    $('#main').innerHTML = `<div class="wrap"><div class="empty">没有找到这条资料，可能已下架。<br><a class="cta" style="margin-top:14px" href="index.html">返回首页</a></div></div>`;
    return;
  }
  track('view:' + it.id);
  const pwd = it.pwd || '';
  const url = it.shareUrl ? (it.pwd ? it.shareUrl + '?pwd=' + encodeURIComponent(it.pwd) : it.shareUrl) : '#';
  setMeta(`${it.title} - 学习资料站`, `${it.desc || it.title}｜${catName(it.category)}·夸克网盘转存，永久有效。`);
  const related = state.items.filter(x => x.id !== it.id && x.category === it.category).slice(0, 4);
  $('#main').innerHTML = `<div class="wrap">
    <div class="crumb"><a href="index.html">首页</a> / <a href="category.html?c=${it.category}">${esc(catName(it.category))}</a>${it.subcategory ? ' / <a href="category.html?c=' + it.category + '&s=' + it.subcategory + '">' + esc(subName(it.category, it.subcategory)) + '</a>' : ''} / ${esc(it.title)}</div>
    <div class="detail">
      <div class="panel">
        <h1>${iconOf(it)} ${esc(it.title)}</h1>
        <div class="tags">${(it.tags || []).map(t => `<span class="tag">#${esc(t)}</span>`).join('')}</div>
        <dl class="kv">
          <dt>分类</dt><dd>${esc(catName(it.category))}</dd>
          ${it.subcategory ? `<dt>方向</dt><dd>${esc(subName(it.category, it.subcategory))}</dd>` : ''}
          ${it.size ? `<dt>大小</dt><dd>${esc(it.size)}</dd>` : ''}
          <dt>格式</dt><dd>${esc(it.formats || '文档 / 视频 / 压缩包')}</dd>
          <dt>更新时间</dt><dd>${esc(it.updatedAt || '—')}</dd>
        </dl>
        <h2 style="font-size:16px;margin:22px 0 6px">资料简介</h2>
        <p style="color:#3a3f47;font-size:14.5px">${esc(it.desc || '暂无简介。')}</p>
      </div>
      <aside class="cta-box panel">
        <button class="big" onclick="openShare('${esc(url)}', '${esc(it.id)}')">⬇ 转存到我的夸克网盘</button>
        <button class="fav-btn${isFav(it.id) ? ' on' : ''}" id="fav-btn" type="button" onclick="toggleFavClick('${esc(it.id)}')"><span class="fav-star">${isFav(it.id) ? '★' : '☆'}</span> ${isFav(it.id) ? '已收藏' : '收藏'}</button>
        <p class="sub">免费 · 永久有效 · 一键保存</p>
        ${pwd ? `<div class="copy"><input id="pwd" readonly value="${esc(pwd)}"><button onclick="copyPwd()">复制提取码</button></div>` : ''}
        <div class="hint">
          <b>怎么用？</b><br>
          1. 点上面按钮打开夸克分享页<br>
          2. 登录夸克账号，点「保存到我的网盘」<br>
          3. 之后在夸克 App 里随时查看
        </div>
      </aside>
    </div>
    ${related.length ? `<div class="sec-title">相关推荐</div><div class="grid">${related.map(cardHTML).join('')}</div>` : ''}
  </div>`;
}

function openShare(url, id) {
  if (!url || url === '#') { alert('示例数据：真实转存链接待上线。'); return; }
  track('get:' + (id || qs('id')));
  window.open(url, '_blank', 'noopener');
}
function copyPwd() {
  const i = $('#pwd'); if (!i) return;
  i.select(); document.execCommand('copy');
  if (navigator.clipboard) navigator.clipboard.writeText(i.value).catch(() => {});
  const b = event.target; const old = b.textContent; b.textContent = '已复制 ✓'; setTimeout(() => b.textContent = old, 1500);
}
window.openShare = openShare; window.copyPwd = copyPwd;

function favItemHTML(it) {
  return `<div class="fav-item">${cardHTML(it)}<button class="fav-del" type="button" title="取消收藏" onclick="removeFavClick('${esc(it.id)}')">✕ 取消收藏</button></div>`;
}

function renderFavorites() {
  setMeta('我的收藏 - 学习资料站', '你在学习资料站收藏的夸克网盘资料，只保存在你自己的浏览器里。');
  const list = favs.map(f => state.items.find(x => x.id === f.id) || f);
  const body = list.length
    ? `<div class="grid">${list.map(favItemHTML).join('')}</div>`
    : `<div class="empty">还没有收藏。去资料详情页点「☆ 收藏」，下次就能在这里找到。<br><a class="cta" style="margin-top:14px" href="index.html">去逛逛资料库</a></div>`;
  $('#main').innerHTML = `<div class="wrap">
    <div class="crumb"><a href="index.html">首页</a> / 我的收藏</div>
    <div class="sec-title">⭐ 我的收藏 <small>共 ${list.length} 条 · 只存在你的浏览器里</small></div>
    ${body}
  </div>`;
}
/* ---------- 搜索（模糊匹配：归一化 + 级联分层命中即停；无依赖） ---------- */
// 为什么级联而不加权求和：加权会让低级匹配污染高级结果（"2055" 在长数字串里被子序列随便命中）。
// 顺序即优先级，任一层有命中就返回，不再往下掉级。最后两层的容错只在前几层全空时才触达，
// 于是「容错」与「噪声」不再共用同一根旋钮。
const PUNCT_RE = /[\s\u00a0\-_·:：,，.。!！?？'"“”‘’()（）[\]{}【】<>/\\|+*&@#$%^~`;；]/g;
const norm = s => String(s == null ? '' : s).normalize('NFKC').toLowerCase().replace(PUNCT_RE, '');
const isAscii = q => /^[\x20-\x7e]+$/.test(q);
function editWithin(a, b, max) {
  if (Math.abs(a.length - b.length) > max) return false;
  if (a === b) return true;
  const m = a.length, n = b.length;
  let prev = new Array(n + 1), cur = new Array(n + 1);
  for (let j = 0; j <= n; j++) prev[j] = j;
  for (let i = 1; i <= m; i++) {
    cur[0] = i; let rowMin = cur[0];
    for (let j = 1; j <= n; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost);
      if (cur[j] < rowMin) rowMin = cur[j];
    }
    if (rowMin > max) return false;
    const t = prev; prev = cur; cur = t;
  }
  return prev[n] <= max;
}
const isSubseq = (hay, needle) => { let i = 0; for (let k = 0; k < hay.length && i < needle.length; k++) if (hay[k] === needle[i]) i++; return i === needle.length; };

// subcategory slug 本身是拼音（gaokao/zhongkao/shuxue/ppt…），纳入匹配面 = 免费一层拼音检索
let SINDEX = null;
function buildSearchIndex() {
  SINDEX = state.items.map(it => ({
    it,
    t: norm(it.title),
    d: norm(it.desc),
    g: norm((it.tags || []).join(' ')),
    c: norm(it.category),
    s: norm(it.subcategory),
    rank: Number(String(it.updatedAt || '').replace(/-/g, '')) || 0,
  }));
}
const STIERS = [
  { name: 'equal', score: (r, q) => (r.t === q ? 100 : 0) + (r.s === q ? 40 : 0) },
  { name: 'prefix', score: (r, q) => (r.t.startsWith(q) ? 80 : 0) + (r.s.startsWith(q) ? 45 : 0) + (r.g.startsWith(q) ? 35 : 0) },
  { name: 'contains', score: (r, q) => (r.t.includes(q) ? 60 : 0) + (r.g.includes(q) ? 40 : 0) + (r.s.includes(q) ? 38 : 0) + (r.c.includes(q) ? 15 : 0) + (r.d.includes(q) ? 20 : 0) },
  { name: 'subsequence', when: (q, a) => !a && q.length >= 3, score: (r, q) => (isSubseq(r.t, q) ? 30 : 0) },
  { name: 'typo', when: q => q.length >= 3, score: (r, q) => (editWithin(r.t, q, 1) ? 10 : 0) },
];
function searchItems(rawQ, limit) {
  const q = norm(rawQ);
  if (!q) return { total: 0, hits: [], tier: 'empty' };
  if (!SINDEX) buildSearchIndex();
  const ascii = isAscii(q);
  for (const tier of STIERS) {
    if (tier.when && !tier.when(q, ascii)) continue;
    const m = [];
    for (const r of SINDEX) { const s = tier.score(r, q); if (s > 0) m.push({ r, s }); }
    if (!m.length) continue;
    m.sort((a, b) => b.s - a.s || b.r.rank - a.r.rank);
    const hits = m.map(x => x.r.it);
    return { total: hits.length, hits: limit ? hits.slice(0, limit) : hits, tier: tier.name };
  }
  return { total: 0, hits: [], tier: 'none' };
}

/* ---------- 搜索下拉（实时结果，点击进详情页） ---------- */
let sdropEl = null;
function ensureDrop() {
  if (sdropEl) return sdropEl;
  sdropEl = document.createElement('div');
  sdropEl.className = 'sdrop';
  sdropEl.hidden = true;
  document.body.appendChild(sdropEl);
  return sdropEl;
}
function hlText(text, q) {
  const i = String(text).toLowerCase().indexOf(String(q).toLowerCase());
  if (i < 0) return esc(text);
  return esc(text.slice(0, i)) + '<mark>' + esc(text.slice(i, i + q.length)) + '</mark>' + esc(text.slice(i + q.length));
}
function placeDrop(input) {
  const r = input.getBoundingClientRect();
  const w = Math.max(260, r.width);
  sdropEl.style.left = Math.max(8, Math.min(r.left, window.innerWidth - w - 8)) + 'px';
  sdropEl.style.top = (r.bottom + 6) + 'px';
  sdropEl.style.width = w + 'px';
}
function attachSearch(input) {
  if (!input) return;
  input.setAttribute('autocomplete', 'off');
  let active = -1, items = [];
  const close = () => { if (sdropEl) sdropEl.hidden = true; active = -1; };
  const render = () => {
    const q = input.value.trim();
    if (!q) { close(); return; }
    const res = searchItems(q, 8);
    items = res.hits;
    const box = ensureDrop();
    placeDrop(input);
    if (!items.length) {
      box.innerHTML = `<div class="sdrop-empty">未找到「${esc(q)}」相关资源</div>`;
    } else {
      box.innerHTML = `<div class="sdrop-meta">${res.total} 条结果</div>` +
        items.map((it, i) => `<a class="sdrop-item${i === active ? ' on' : ''}" href="resource.html?id=${encodeURIComponent(it.id)}" data-i="${i}">` +
          `<span class="sdrop-ico">${iconOf(it)}</span>` +
          `<span class="sdrop-title">${hlText(it.title, q)}</span>` +
          `<span class="sdrop-cat">${esc(catName(it.category))}</span>` +
        `</a>`).join('') +
        `<a class="sdrop-more" href="search.html?q=${encodeURIComponent(q)}">查看全部 ${res.total} 条 →</a>`;
    }
    box.hidden = false;
  };
  input.addEventListener('input', () => { active = -1; render(); });
  input.addEventListener('focus', render);
  input.addEventListener('keydown', e => {
    if (!sdropEl || sdropEl.hidden) return;
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      if (!items.length) return;
      e.preventDefault();
      active = (active + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
      sdropEl.querySelectorAll('.sdrop-item').forEach((el, i) => el.classList.toggle('on', i === active));
    } else if (e.key === 'Enter') {
      if (active >= 0 && items[active]) { e.preventDefault(); location.href = 'resource.html?id=' + encodeURIComponent(items[active].id); }
    } else if (e.key === 'Escape') { close(); }
  });
  input.addEventListener('blur', () => setTimeout(close, 160));
}
function initSearch() {
  $$('.hd-search input, .hero-search input').forEach(attachSearch);
}
document.addEventListener('mousedown', e => { if (sdropEl && !sdropEl.hidden && sdropEl.contains(e.target)) e.preventDefault(); });
window.addEventListener('scroll', () => {
  if (!sdropEl || sdropEl.hidden) return;
  const inp = document.querySelector('.hd-search input, .hero-search input');
  if (!inp) return;
  const r = inp.getBoundingClientRect();
  if (r.bottom < 0 || r.top > window.innerHeight) { sdropEl.hidden = true; return; }
  placeDrop(inp);
}, true);

boot();
