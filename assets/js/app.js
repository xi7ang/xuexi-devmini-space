/* 学习资源站 — 纯静态前端 */
const $ = (s, r = document) => r.querySelector(s);
const esc = (s = '') => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const qs = k => new URLSearchParams(location.search).get(k);

const state = { items: [], tax: {}, meta: {}, cat: 'all', sub: 'all' };

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
  if (page === 'home') renderHome();
  else if (page === 'category') renderCategory();
  else if (page === 'search') renderSearch();
  else if (page === 'resource') renderResource();
}

function headerHTML() {
  const page = document.body.dataset.page;
  const on = p => (page === p ? ' class="on"' : '');
  const navs = Object.entries(state.tax).map(([slug, c]) =>
    `<a href="category.html?c=${slug}"${on('category-' + slug)}>${esc(c.name)}</a>`).join('');
  return `<div class="wrap hd-inner">
    <a class="logo" href="index.html">📚 <span>学习<b>资源站</b></span></a>
    <nav class="hd-nav"><a href="index.html"${on('home')}>首页</a>${navs}</nav>
    <form class="hd-search" onsubmit="location.href='search.html?q='+encodeURIComponent(this.q.value);return false">
      <input name="q" placeholder="搜索资料 / 考试 / 技能" value="${esc(qs('q') || '')}">
    </form>
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
      <h3>${esc(it.title)} ${demo}</h3>
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
  const low = q.toLowerCase();
  const items = q ? state.items.filter(it => {
    const hay = [it.title, it.desc, it.category, it.subcategory, catName(it.category), subName(it.category, it.subcategory), ...(it.tags || [])].join(' ').toLowerCase();
    return hay.includes(low);
  }) : state.items;
  $('#main').innerHTML = `<div class="wrap">
    <div class="crumb"><a href="index.html">首页</a> / 搜索</div>
    <div class="sec-title">搜索「${esc(q)}」 <small>找到 ${items.length} 条</small></div>
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
  const pwd = it.pwd || '';
  const url = it.shareUrl || '#';
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
        <button class="big" onclick="openShare('${esc(url)}')">⬇ 转存到我的夸克网盘</button>
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

function openShare(url) {
  if (!url || url === '#') { alert('示例数据：真实转存链接待上线。'); return; }
  window.open(url, '_blank', 'noopener');
}
function copyPwd() {
  const i = $('#pwd'); if (!i) return;
  i.select(); document.execCommand('copy');
  if (navigator.clipboard) navigator.clipboard.writeText(i.value).catch(() => {});
  const b = event.target; const old = b.textContent; b.textContent = '已复制 ✓'; setTimeout(() => b.textContent = old, 1500);
}
window.openShare = openShare; window.copyPwd = copyPwd;

boot();
