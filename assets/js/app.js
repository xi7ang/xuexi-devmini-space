/* 学习资源站 — 纯静态前端 */
const $ = (s, r = document) => r.querySelector(s);
const esc = (s = '') => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const qs = k => new URLSearchParams(location.search).get(k);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

const state = { items: [], tax: {}, meta: {}, cat: 'all', sub: 'all' };
// TG 频道入口（公告弹窗 + 导航栏共用）
const TG_URL = 'https://t.me/aixuexi66';
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
function toggleFavClick(id) {
  const it = state.items.find(x => x.id === id);
  if (!it) return;
  const on = toggleFav(it);
  updateFavBtn(id);
  track((on ? 'fav:' : 'unfav:') + id);
}
function removeFavClick(id) { removeFav(id); renderFavorites(); }

/* ---------- 公告弹窗（数据在 data/site.json） ---------- */
const ANN_KEY = 'xx-announcement-dismissed';
function localDateKey() { const n = new Date(), p = v => String(v).padStart(2, '0'); return `${n.getFullYear()}-${p(n.getMonth() + 1)}-${p(n.getDate())}`; }
function linkify(text) {
  const e = esc(text).replace(/(https?:\/\/[^\s<)】]+)/g, u => `<a href="${u}" target="_blank" rel="noopener">${u}</a>`);
  return e.replace(/\n/g, '<br>');
}
function toggleAnn(i) {
  const body = document.getElementById('ann-body-' + i);
  const chev = document.getElementById('ann-chev-' + i);
  if (!body) return;
  const open = body.style.display !== 'none';
  body.style.display = open ? 'none' : '';
  if (chev) chev.textContent = open ? '▸' : '▾';
}
function annEsc(e) { if (e.key === 'Escape') closeAnn(); }
function closeAnn() {
  const m = document.getElementById('ann-mask');
  if (m) m.remove();
  document.removeEventListener('keydown', annEsc);
}
function closeAnnToday() {
  try {
    const m = document.getElementById('ann-mask');
    if (m) localStorage.setItem(ANN_KEY, JSON.stringify({ version: m.dataset.version || '', date: localDateKey() }));
  } catch (e) {}
  closeAnn();
}
async function loadAnnouncement() {
  let site = null;
  try { const r = await fetch('data/site.json', { cache: 'no-cache' }); if (r.ok) site = await r.json(); } catch (e) { return; }
  const a = site && site.announcementModal;
  if (!a || !a.enabled) return;
  const items = Array.isArray(a.items) ? a.items : [];
  if (!a.content && !items.length) return;
  const version = a.version || ((a.title || '') + ':' + (a.content || ''));
  try { const d = JSON.parse(localStorage.getItem(ANN_KEY) || 'null'); if (d && d.version === version && d.date === localDateKey()) return; } catch (e) {}
  const timeline = items.length ? `<div class="ann-timeline">${items.map((it, i) => `
    <div class="ann-tl${i === 0 ? ' latest' : ''}">
      <button type="button" class="ann-tl-head" aria-expanded="${i === 0}" data-ann-i="${i}">
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
    <button class="ann-close" type="button" title="关闭" aria-label="关闭公告">✕</button>
    <div class="ann-icon">📢</div>
    <p class="ann-eyebrow">XUEXI NOTICE</p>
    <h2 id="ann-title">${esc(a.title || '站点公告')}</h2>
    <div class="ann-socials">
      <a class="ann-social ann-social--tg" href="${TG_URL}" target="_blank" rel="noreferrer">
        <svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor" aria-hidden="true"><path d="M21.9 3.6c.3-1.2-.9-2.2-2-1.7L2.7 9.8c-1.2.5-1.1 2.2.1 2.6l4.8 1.6 1.8 5.7c.4 1.1 1.8 1.4 2.6.6l2.5-2.5 4.7 3.5c1 .7 2.4.2 2.7-1l2.9-16.7zM9 14.2l8.5-6.9c.3-.2.6.2.4.5l-6.6 7.2c-.3.3-.8.4-1.2.3l-2.3-.8 1.2-.3z"/></svg>
        <span>TG频道</span>
      </a>
    </div>
    ${timeline}
    <div class="ann-actions">
      <button class="ann-btn ghost" type="button" data-act="dismiss-today">今日关闭</button>
      <button class="ann-btn primary" type="button" data-act="close">关闭</button>
    </div>
  </section>`;
  box.addEventListener('click', e => { if (e.target === box) closeAnn(); });
  box.querySelectorAll('.ann-tl-head').forEach(el => el.addEventListener('click', () => toggleAnn(Number(el.dataset.annI))));
  const aClose = box.querySelector('.ann-close'); if (aClose) aClose.addEventListener('click', () => closeAnn());
  const aDismiss = box.querySelector('[data-act="dismiss-today"]'); if (aDismiss) aDismiss.addEventListener('click', () => closeAnnToday());
  const aOk = box.querySelector('[data-act="close"]'); if (aOk) aOk.addEventListener('click', () => closeAnn());
  document.addEventListener('keydown', annEsc);
  document.body.appendChild(box);
}

async function boot() {
  let res, tax;
  try {
    // no-cache = 存下来但每次校验（304 时几乎零流量）；别用 no-store（每次全量重下）
    [res, tax] = await Promise.all([
      fetch('data/resources.json', { cache: 'no-cache' }).then(r => { if (!r.ok) throw new Error('resources ' + r.status); return r.json(); }),
      fetch('data/taxonomy.json', { cache: 'no-cache' }).then(r => { if (!r.ok) throw new Error('taxonomy ' + r.status); return r.json(); })
    ]);
  } catch (e) {
    const m = $('#main');
    if (m) m.innerHTML = '<div class="wrap"><div class="empty">数据加载失败，请刷新重试 🙏</div></div>';
    return;
  }
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
    <div class="hd-right">
      <a class="hd-fav" href="favorites.html" title="我的收藏" aria-label="我的收藏">
        <span class="hd-fav-star">⭐</span><span class="hd-fav-text">收藏</span>${favCount() ? `<b>${favCount()}</b>` : ''}
      </a>
      <a class="hd-tg" href="${TG_URL}" target="_blank" rel="noreferrer" title="TG 频道" aria-label="TG 频道">
        <svg class="hd-tg-icon" viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden="true"><path d="M21.9 3.6c.3-1.2-.9-2.2-2-1.7L2.7 9.8c-1.2.5-1.1 2.2.1 2.6l4.8 1.6 1.8 5.7c.4 1.1 1.8 1.4 2.6.6l2.5-2.5 4.7 3.5c1 .7 2.4.2 2.7-1l2.9-16.7zM9 14.2l8.5-6.9c.3-.2.6.2.4.5l-6.6 7.2c-.3.3-.8.4-1.2.3l-2.3-.8 1.2-.3z"/></svg>
        <span class="hd-tg-text">TG频道</span>
      </a>
    </div>
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

function setMeta(title, desc, canonical, robots) {
  document.title = title;
  if (desc) {
    let d = document.head.querySelector('meta[name=description]');
    if (!d) { d = document.createElement('meta'); d.setAttribute('name', 'description'); document.head.appendChild(d); }
    d.setAttribute('content', desc);
  }
  let c = document.head.querySelector('link[rel=canonical]');
  if (!c) { c = document.createElement('link'); c.rel = 'canonical'; document.head.appendChild(c); }
  // canonical 不能照抄 location.search：分类的 ?s= 组合、搜索的 ?q= 会被各自判成独立页
  c.href = canonical || location.origin + location.pathname;
  let r = document.head.querySelector('meta[name=robots]');
  if (robots) {
    if (!r) { r = document.createElement('meta'); r.setAttribute('name', 'robots'); document.head.appendChild(r); }
    r.setAttribute('content', robots);
  } else if (r) { r.setAttribute('content', 'index,follow'); }
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
// 品类色：三类专属色，用于卡片色条 / 图标底色 / 详情页 chips
const CAT_COLOR = { exam: '#ff6b35', study: '#2f6bff', office: '#16a34a' };
const catColor = c => CAT_COLOR[c] || '#8a8f98';
function findSubOf(cat, sub) {
  const t = state.tax[cat];
  return t && (t.subs || []).find(x => x.slug === sub);
}

function cardHTML(it) {
  const href = `resource.html?id=${encodeURIComponent(it.id)}`;
  const tags = (it.tags || []).slice(0, 3).map(t => `<span class="tag">#${esc(t)}</span>`).join('');
  const demo = it.demo ? '<span class="badge">示例</span>' : '';
  const today = it.updatedAt === localDateKey();
  return `<a class="card" href="${href}">
    <span class="card-bar" style="background:${catColor(it.category)}" aria-hidden="true"></span>
    <div class="card-top">
      <div class="card-ico" style="background:${catColor(it.category)}1a">${iconOf(it)}</div>
      <h3>${esc(it.title)} ${demo}${today ? '<span class="badge badge-new">今日上新</span>' : ''}</h3>
    </div>
    <p class="card-desc">${esc(it.desc || '')}</p>
    <div class="tags">${tags}</div>
    <div class="card-foot">
      <span class="card-meta">${esc(catName(it.category))}${it.subcategory ? ' · ' + esc(subName(it.category, it.subcategory)) : ''}${it.updatedAt ? ' · ' + esc(String(it.updatedAt).slice(5)) : ''}</span>
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
    '免费夸克网盘学习资料：高考真题、中考真题、中小学试卷与知识点、PPT 办公模板，一键转存、永久有效。',
    location.origin + '/');
  const n = state.items.filter(x => !x.demo).length || state.items.length;
  const subs = Object.values(state.tax).reduce((a, c) => a + (c.subs ? c.subs.length : 0), 0);
  const todayNew = state.items.filter(x => x.updatedAt === localDateKey()).length;
  $('#main').innerHTML = `
  <section class="hero">
    <div class="wrap">
      <h1>考试真题 · 中小学 · <em>办公素材</em></h1>
      <p>高考/中考真题、中小学试卷与知识点、PPT 办公模板，一键转存到自己的夸克网盘，永久有效。</p>
      <form class="hero-search" onsubmit="location.href='search.html?q='+encodeURIComponent(this.q.value);return false">
        <input name="q" placeholder="搜高考数学真题、三年级语文、述职 PPT…">
        <button>搜索</button>
      </form>
      <div class="hero-new">
        <a class="hero-new__pill" href="#latest">🔥 今日上新 <b>${todayNew}</b> 条 · 看最新 →</a>
      </div>
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
    <div id="latest"></div>
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
  setMeta(`${t ? t.name : '全部资料'} - 学习资料站`, `${t ? (t.desc || t.name) : '全部资料'}｜夸克网盘资源免费转存。`, `${location.origin}/category.html?c=${state.cat}`);
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
  setMeta(`搜索「${q}」 - 学习资料站`, `在学习资料站搜索「${q}」的夸克网盘资源。`, `${location.origin}/search.html`, 'noindex,follow');
  const low = q.toLowerCase();
  const items = q ? state.items.filter(it => {
    const hay = [it.title, it.desc, it.category, it.subcategory, catName(it.category), subName(it.category, it.subcategory), ...(it.tags || [])].join(' ').toLowerCase();
    return hay.includes(low);
  }) : state.items;
  const body = items.length
    ? gridOf(items)
    : `<div class="empty-block">
        <div class="empty-block__ico">🔍</div>
        <p>没找到「${esc(q)}」相关的资料</p>
        <p class="empty-block__hint">换个关键词试试，或直接逛分类：</p>
        <div class="chips chips--center">${Object.entries(state.tax).map(([slug, c]) => `<a class="chip" href="category.html?c=${slug}">${esc(c.name)}</a>`).join('')}</div>
      </div>`;
  $('#main').innerHTML = `<div class="wrap">
    <div class="crumb"><a href="index.html">首页</a> / 搜索</div>
    <div class="sec-title">搜索「${esc(q)}」 <small>找到 ${items.length} 条</small></div>
    ${body}
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
  setMeta(`${it.title} - 学习资料站`, `${it.desc || it.title}｜${catName(it.category)}·夸克网盘转存，永久有效。`, `${location.origin}/resource.html?id=${encodeURIComponent(it.id)}`);
  const related = state.items.filter(x => x.id !== it.id && x.category === it.category)
    .sort((a, b) => String(b.updatedAt || '').localeCompare(String(a.updatedAt || '')))
    .slice(0, 4);
  const favOn = isFav(it.id);
  $('#main').innerHTML = `<div class="wrap">
    <div class="crumb"><a href="index.html">首页</a> / <a href="category.html?c=${it.category}">${esc(catName(it.category))}</a>${it.subcategory ? ' / <a href="category.html?c=' + it.category + '&s=' + it.subcategory + '">' + esc(subName(it.category, it.subcategory)) + '</a>' : ''} / ${esc(it.title)}</div>
    <div class="detail">
      <div class="panel">
        <h1>${iconOf(it)} ${esc(it.title)}</h1>
        <div class="tags">${(it.tags || []).map(t => `<span class="tag">#${esc(t)}</span>`).join('')}</div>
        <div class="info-chips">
          <span class="info-chip info-chip--cat" style="border-color:${catColor(it.category)}66;color:${catColor(it.category)}">${iconOf(it)} ${esc(catName(it.category))}</span>
          ${it.subcategory ? `<span class="info-chip">${esc(subName(it.category, it.subcategory))}</span>` : ''}
          ${it.size ? `<span class="info-chip">📦 ${esc(it.size)}</span>` : ''}
          <span class="info-chip">📄 ${esc(it.formats || '文档 / 视频 / 压缩包')}</span>
          <span class="info-chip">🗓 ${esc(it.updatedAt || '—')}</span>
        </div>
        <h2 style="font-size:16px;margin:22px 0 6px">资料简介</h2>
        <p style="color:#3a3f47;font-size:14.5px">${esc(it.desc || '暂无简介。')}</p>
      </div>
      <aside class="cta-box panel">
        <button class="big" id="share-btn" type="button" data-url="${esc(url)}" data-id="${esc(it.id)}">⬇ 转存到我的夸克网盘</button>
        <button class="fav-btn${favOn ? ' on' : ''}" id="fav-btn" type="button" data-id="${esc(it.id)}"><span class="fav-star">${favOn ? '★' : '☆'}</span> ${favOn ? '已收藏' : '收藏'}</button>
        <p class="sub">免费 · 永久有效 · 一键保存</p>
        ${pwd ? `<div class="copy"><input id="pwd" readonly value="${esc(pwd)}"><button id="copy-pwd" type="button">复制提取码</button></div>` : ''}
        <div class="hint">
          <b>怎么用？</b><br>
          1. 点上面按钮打开夸克分享页<br>
          2. 登录夸克账号，点「保存到我的网盘」<br>
          3. 之后在夸克 App 里随时查看
        </div>
      </aside>
    </div>
    ${related.length ? `<div class="sec-title">同类最新 <small>看更多同类型资料</small></div><div class="grid">${related.map(cardHTML).join('')}</div>` : ''}
  </div>`;
  // 事件绑定代替内联 onclick（esc 是 HTML 转义，不是 JS 字符串转义，拼进 onclick 靠运气）
  const sb = $('#share-btn'); if (sb) sb.addEventListener('click', () => openShare(sb.dataset.url, sb.dataset.id, sb));
  const fb = $('#fav-btn'); if (fb) fb.addEventListener('click', () => toggleFavClick(fb.dataset.id));
  const cp = $('#copy-pwd'); if (cp) cp.addEventListener('click', () => copyPwd(cp));
}

function openShare(url, id, btn) {
  if (!url || url === '#') { alert('示例数据：真实转存链接待上线。'); return; }
  track('get:' + (id || qs('id')));
  window.open(url, '_blank', 'noopener');
  // 点击后兜底转存按钮：网盘被拦截或加载慢时，按钮变可再点提示（转化效率最高的改进点）
  const b = btn || document.querySelector('.cta-box .big');
  if (b && !b.classList.contains('got')) { b.classList.add('got'); b.innerHTML = '✅ 已跳转，没打开点这里'; }
}
function copyPwd(btn) {
  const i = $('#pwd'); if (!i) return;
  i.select();
  try { document.execCommand('copy'); } catch (e) {}
  if (navigator.clipboard) navigator.clipboard.writeText(i.value).catch(() => {});
  // 不依赖隐式全局 event（非标准）；按钮从参数来
  if (btn) { const old = btn.textContent; btn.textContent = '已复制 ✓'; setTimeout(() => btn.textContent = old, 1500); }
}

function favItemHTML(it) {
  return `<div class="fav-item">${cardHTML(it)}<button class="fav-del" type="button" title="取消收藏" data-id="${esc(it.id)}">✕ 取消收藏</button></div>`;
}

function renderFavorites() {
  setMeta('我的收藏 - 学习资料站', '你在学习资料站收藏的夸克网盘资料，只保存在你自己的浏览器里。', `${location.origin}/favorites.html`, 'noindex,nofollow');
  const list = favs.map(f => state.items.find(x => x.id === f.id) || f);
  const body = list.length
    ? `<div class="grid">${list.map(favItemHTML).join('')}</div>`
    : `<div class="empty">还没有收藏。去资料详情页点「☆ 收藏」，下次就能在这里找到。<br><a class="cta" style="margin-top:14px" href="index.html">去逛逛资料库</a></div>`;
  $('#main').innerHTML = `<div class="wrap">
    <div class="crumb"><a href="index.html">首页</a> / 我的收藏</div>
    <div class="sec-title">⭐ 我的收藏 <small>共 ${list.length} 条 · 只存在你的浏览器里</small></div>
    ${body}
  </div>`;
  $$('.fav-del').forEach(b => b.addEventListener('click', () => removeFavClick(b.dataset.id)));
}

boot();
