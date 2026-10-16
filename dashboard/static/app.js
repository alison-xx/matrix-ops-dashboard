/* 矩阵运营工作台 —— 单页应用
   图表：ECharts 5.6.0；动效：GSAP 3.12.5（都在 static/vendor，本地加载）。
   任一库没加载到，页面照常工作，只是没有图表动画/界面动效。 */
'use strict';

/* ---------- 常量 ---------- */
const PLAT = {
  dy: { name: '抖音' }, ks: { name: '快手' }, sph: { name: '视频号' }, bili: { name: 'B站' }, xhs: { name: '小红书' },
  wb: { name: '微博' }, zh: { name: '知乎' }, gzh: { name: '公众号' },
};
const PLAT_ORDER = ['dy', 'ks', 'sph', 'bili', 'xhs', 'wb', 'zh', 'gzh'];
const ICON = {
  overview: '<rect x="3.5" y="3.5" width="7" height="7" rx="1.6"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.6"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.6"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.6"/>',
  accounts: '<circle cx="12" cy="8.5" r="3.8"/><path d="M4.5 20c1.4-3.6 4.2-5.4 7.5-5.4s6.1 1.8 7.5 5.4"/>',
  content: '<rect x="3.5" y="4.5" width="17" height="15" rx="2.2"/><circle cx="9" cy="10" r="1.8"/><path d="M20.5 15.5l-4.8-4.6-8.7 8.6"/>',
  data: '<path d="M4 20h16"/><path d="M7 16.5V11M12 16.5V6.5M17 16.5v-4"/>',
  engagement: '<path d="M4.5 5.5h15v10h-8.5l-4.5 3.5v-3.5h-2z"/><path d="M8.5 10.5h7"/>',
  hot: '<path d="M12 3.5c.8 2.7 4.8 4.6 4.8 9.4a4.8 4.8 0 0 1-9.6 0c0-1.9 1-3.4 2-4.3.2 1.4.9 2.4 1.9 2.9-.2-2.8.1-5.6.9-8z"/>',
  plan: '<path d="M6 21V4"/><path d="M6 4.5h11.5l-2.2 4 2.2 4H6"/>',
  reports: '<path d="M7 3.5h7l4.5 4.5v12.5H7z"/><path d="M14 3.5V8h4.5M9.8 12.5h5.5M9.8 16h5.5"/>',
  more: '<circle cx="5.5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="18.5" cy="12" r="1.3"/>',
  growth: '<path d="M4 17.5l5.2-5.2 3.6 3.6L20 8.7"/><path d="M14.8 8.5H20v5.2"/>',
  calendar: '<rect x="3.5" y="5" width="17" height="15.5" rx="2.2"/><path d="M3.5 9.8h17M8 3.2v3.6M16 3.2v3.6"/><path d="M7.5 13.5h2M11 13.5h2M14.5 13.5h2M7.5 16.8h2M11 16.8h2"/>',
  search: '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4 4"/>',
  sun: '<circle cx="12" cy="12" r="3.8"/><path d="M12 2.8v2.2M12 19v2.2M2.8 12h2.2M19 12h2.2M5.5 5.5l1.6 1.6M16.9 16.9l1.6 1.6M5.5 18.5l1.6-1.6M16.9 7.1l1.6-1.6"/>',
  moon: '<path d="M19.5 14.5A7.8 7.8 0 0 1 9.5 4.5a7.8 7.8 0 1 0 10 10z"/>',
  system: '<rect x="3.5" y="4.5" width="17" height="11.5" rx="2"/><path d="M8.5 20h7M12 16v4"/>',
  copy: '<rect x="8.5" y="8.5" width="11" height="11" rx="2"/><path d="M15.5 8.5V6a1.5 1.5 0 0 0-1.5-1.5H6A1.5 1.5 0 0 0 4.5 6v8A1.5 1.5 0 0 0 6 15.5h2.5"/>',
  link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
  ext: '<path d="M13.5 4.5h6v6"/><path d="M19.5 4.5l-8 8"/><path d="M17.5 13.5v5a1.5 1.5 0 0 1-1.5 1.5H6A1.5 1.5 0 0 1 4.5 18.5V8.5A1.5 1.5 0 0 1 6 7h5"/>',
  left: '<path d="M14.5 6l-6 6 6 6"/>',
  right: '<path d="M9.5 6l6 6-6 6"/>',
  doc: '<path d="M7 3.5h7l4.5 4.5v12.5H7z"/><path d="M14 3.5V8h4.5"/>',
  bolt: '<path d="M13 3.5L5.5 13.5H12l-1 7 7.5-10H12z"/>',
  keyboard: '<rect x="2.5" y="6" width="19" height="12" rx="2"/><path d="M6 10h.01M9 10h.01M12 10h.01M15 10h.01M18 10h.01M7 14h10"/>',
  grid: '<rect x="3.5" y="3.5" width="7" height="7" rx="1.6"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.6"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.6"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.6"/>',
  list: '<path d="M8.5 6.5h12M8.5 12h12M8.5 17.5h12"/><circle cx="4.5" cy="6.5" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="17.5" r="1"/>',
  download: '<path d="M12 4v11"/><path d="M7.5 10.5L12 15l4.5-4.5"/><path d="M4.5 19.5h15"/>',
};
const PAGES = [
  { id: 'overview', name: '总览', key: '1' }, { id: 'growth', name: '增长', key: '2' }, { id: 'calendar', name: '日历', key: '3' },
  { id: 'content', name: '内容', key: '4' }, { id: 'data', name: '数据', key: '5' }, { id: 'accounts', name: '账号', key: '6' },
  { id: 'engagement', name: '互动', key: '7' }, { id: 'hot', name: '热点', key: '8' }, { id: 'plan', name: '运营计划', key: '9' },
  { id: 'reports', name: '日报', key: '0' },
];
const PAGE_DESC = {
  overview: '今天的粉丝、发布进度和待处理', growth: '粉丝走势、目标进度、各账号投入产出', calendar: '周排期、30 天发布心跳、发布质量',
  content: '按天看每条内容和成品', data: '作品播放、留存、栏目和时段', accounts: '单个账号的粉丝和作品', engagement: '评论额度和流水',
  hot: '热点雷达和快反记录', plan: '手册、实验、版本和进化', reports: '每日复盘',
};
const MOBILE_MAIN = ['overview', 'calendar', 'content', 'data'];
const BUCKET = {
  done: { label: '已发', g: '✓' }, queue: { label: '排队', g: '◷' }, fail: { label: '失败', g: '✕' },
  warn: { label: '待核实', g: '!' }, muted: { label: '其他', g: '–' },
};
const MODE = { native: '平台定时', dispatch: '到点提交', web: '网页发表', draft: '草稿预览' };
const PTYPE = { video: '视频', imageText: '图文', article: '文章', answer: '回答' };
const EVK = { add: '入账', approve: '审核通过', submit: '提交', link: '回填链接', status: '状态变更', retry: '重试' };
const MLABEL = {
  views: '播放/阅读', likes: '赞', favorites: '收藏', comments: '评论', shares: '转发', follows: '涨粉',
  homepage_visits: '主页访问', completion: '完播率', completion_5s: '5秒完播', bounce_2s: '2秒跳出',
  avg_view_sec: '平均观看秒数', avg_view_ratio: '平均观看占比', duration: '时长（秒）', cover_show: '封面曝光', pics: '图片数', type: '类型',
};
const PCT_KEYS = new Set(['completion', 'completion_5s', 'bounce_2s', 'avg_view_ratio']);

/* ---------- 状态 ---------- */
const S = {
  route: { page: 'overview', arg: null, q: {} },
  data: {}, ui: { sort: {}, tab: {}, openTips: {}, filter: {} },
  lastOk: null, drawerId: null, drawerReturn: null, drawerList: [],
  pendingCount: 0, seenPending: null, rendered: false,
  meta: null, health: null,
};

/* ---------- 工具 ---------- */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => Array.from(el.querySelectorAll(s));
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const isNum = (v) => typeof v === 'number' && isFinite(v);
const fmtN = (v, d = 1) => (isNum(v) ? Number(v).toLocaleString('zh-CN', { maximumFractionDigits: d }) : '—');
const pct = (v, d = 0) => (isNum(v) ? (v * 100).toFixed(d) + '%' : '—');
const hm = (iso) => (iso ? String(iso).slice(11, 16) : '');
const mdShort = (iso) => (iso ? `${String(iso).slice(5, 7)}-${String(iso).slice(8, 10)}` : '');
const WD = '日一二三四五六';
function dayLabel(day) {
  if (!day) return '';
  const d = new Date(day + 'T00:00:00+08:00');
  return `${d.getMonth() + 1}月${d.getDate()}日 周${WD[d.getDay()]}`;
}
function todayStr() { return new Date(Date.now() + 8 * 3600e3).toISOString().slice(0, 10); }
function shiftDay(day, k) {
  const d = new Date(day + 'T12:00:00Z');
  d.setUTCDate(d.getUTCDate() + k);
  return d.toISOString().slice(0, 10);
}
function daysBetween(a, b) { return Math.round((new Date(b + 'T12:00:00Z') - new Date(a + 'T12:00:00Z')) / 864e5); }
function delta(n, label = '') {
  const pre = label ? label + ' ' : '';
  if (!isNum(n)) return `<span class="delta none">${pre}—</span>`;
  if (n > 0) return `<span class="delta up">${pre}+${fmtN(n, 0)}</span>`;
  if (n < 0) return `<span class="delta down">${pre}−${fmtN(-n, 0)}</span>`;
  return `<span class="delta flat">${pre}0</span>`;
}
const ico = (name, cls = '') => `<svg class="ico ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICON[name] || ''}</svg>`;
/* 平台标识：真实品牌图形（vendor/logos），两个抖音号共用一个标识，用账号名区分 */
const logo = (pk, size = '') => {
  const p = PLAT[pk];
  if (!p) return `<span class="pl pl-fallback ${size}" role="img" aria-label="${esc(pk || '其他')}">${esc((pk || '?').slice(0, 1))}</span>`;
  return `<span class="pl pl-${pk} ${size}" role="img" aria-label="${esc(p.name)}" title="${esc(p.name)}"><i></i></span>`;
};
const pill = (bucket, label) => {
  const b = BUCKET[bucket] || BUCKET.muted;
  return `<span class="pill pill-${esc(bucket)}"><span class="g" aria-hidden="true">${b.g}</span>${esc(label || b.label)}</span>`;
};
const who = (pk, name, sub) => `<span class="who">${logo(pk)}<span class="nm">${esc(name)}</span>${sub ? `<span class="pf">${esc(sub)}</span>` : ''}</span>`;
const ext = (url, text) => (url ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(text || url)}</a>` : '');
/* 会动的数字：data-k 是稳定键，刷新时只对变化的那个做强调 */
const cnt = (k, v, d = 0, cls = '') => (isNum(v) ? `<span class="num ${cls}" data-k="${esc(k)}" data-v="${v}" data-d="${d}">${fmtN(v, d)}</span>` : `<span class="num ${cls}">—</span>`);
const bar = (ratio, cls = '', tip = '') => `<span class="bar"${tip ? ` data-tip="${esc(tip)}"` : ''}><i class="${cls}" style="width:${Math.max(0, Math.min(100, ratio * 100)).toFixed(1)}%"></i></span>`;
function errNote(errors) {
  const ks = Object.keys(errors || {});
  if (!ks.length) return '';
  return `<div class="err-note">部分数据源读取失败（${ks.map((k) => esc(k)).join('、')}），对应区块显示为空，其他区块正常。详情：${esc(
    ks.map((k) => `${k}: ${errors[k]}`).join('；').slice(0, 300))}</div>`;
}
const empty = (html) => `<div class="empty">${html}</div>`;
const store = {
  get(k, d) { try { const v = localStorage.getItem('xxdash.' + k); return v ? JSON.parse(v) : d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem('xxdash.' + k, JSON.stringify(v)); } catch { /* 私密窗口等情况忽略 */ } },
};

let toastT = null;
function toast(msg) {
  const el = $('#toast');
  el.textContent = msg;
  el.classList.add('on');
  clearTimeout(toastT);
  toastT = setTimeout(() => el.classList.remove('on'), 1800);
}
async function copyText(text, what = '内容') {
  if (!text) { toast(`没有可复制的${what}`); return; }
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;opacity:0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); } catch { /* 忽略 */ }
    ta.remove();
  }
  toast(`已复制${what}`);
}
/* 把表格数据导出成 CSV（带 BOM，Excel 直接打开不乱码） */
function downloadCSV(name, header, rows) {
  const cell = (v) => {
    const s = v == null ? '' : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const body = '﻿' + [header, ...rows].map((r) => r.map(cell).join(',')).join('\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([body], { type: 'text/csv;charset=utf-8' }));
  a.download = name;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 0);
}
const ago = (iso) => {
  const m = isNum(iso) ? iso : (iso ? Math.round((Date.now() - new Date(iso).getTime()) / 60000) : null);
  if (m == null || !isFinite(m)) return '—';
  if (m < 1) return '刚刚';
  if (m < 60) return `${m} 分钟前`;
  if (m < 1440) return `${Math.floor(m / 60)} 小时${m % 60 >= 10 && m < 600 ? ` ${m % 60} 分` : ''}前`;
  return `${Math.floor(m / 1440)} 天前`;
};

async function api(path) {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), 20000);
  try {
    const r = await fetch(path, { cache: 'no-store', signal: ctl.signal });
    const j = await r.json().catch(() => ({}));
    if (r.status === 401 && j.login) { // 远程站点登录过期：回登录页，登录后回到当前位置
      location.href = j.login + '?next=' + encodeURIComponent(location.pathname + location.search + location.hash);
      throw new Error('需要重新登录');
    }
    if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
    return j;
  } finally {
    clearTimeout(t);
  }
}

/* ---------- 动效（浏览器原生 Web Animations API，不依赖第三方库） ---------- */
const RM = matchMedia('(prefers-reduced-motion: reduce)');
const EASE_OUT = 'cubic-bezier(.22,1,.36,1)';
const EASE_IO = 'cubic-bezier(.65,0,.35,1)';
/* 后台标签页里动画会被节流，这时直接显示最终状态 */
const canMove = () => 'animate' in Element.prototype && !RM.matches && (!document.hidden || window.__forceMotion === true);
/* 一组元素按顺序错开出现；amount 是总错开时长（秒），和设计稿里的 stagger.amount 同义 */
function play(els, keyframes, { duration = 0.5, delay = 0, amount = 0, easing = EASE_OUT } = {}) {
  const list = Array.from(els);
  const step = list.length > 1 ? amount / (list.length - 1) : 0;
  list.forEach((el, i) => {
    try { el.animate(keyframes, { duration: duration * 1000, delay: (delay + i * step) * 1000, easing, fill: 'backwards' }); } catch { /* 老浏览器不支持某些属性就跳过 */ }
  });
}
const Motion = {
  /* 页面入场：顶层区块依次上浮，总时长封顶 0.35s */
  enter(root) {
    if (!canMove()) return;
    const blocks = Array.from(root.children).filter((el) => el.offsetParent !== null);
    play(blocks, { opacity: [0, 1], translate: ['0 12px', '0 0'] }, { duration: 0.55, amount: Math.min(0.35, blocks.length * 0.06) });
    $$('[data-stagger]', root).forEach((box) => {
      const kids = Array.from(box.children).slice(0, 24);
      play(kids, { opacity: [0, 1], translate: ['0 10px', '0 0'] }, { duration: 0.5, delay: 0.08, amount: Math.min(0.4, kids.length * 0.035) });
    });
  },
  /* 进度条、额度条从左生长 */
  bars(root, delay = 0.15) {
    if (!canMove()) return;
    const els = $$('.bar > i, .stackbar > i, .exp .rail > i, .goal-bar > i', root);
    if (els.length) play(els, { scale: ['0 1', '1 1'] }, { duration: 0.9, delay, amount: Math.min(0.45, els.length * 0.012) });
  },
  /* 排期：圆点按时间顺序出现，「现在」竖线自上而下画出 */
  rundown(root) {
    if (!canMove()) return;
    play($$('.rd-track .rd-mk, .rd-track .rd-plan', root), { opacity: [0, 1], scale: [0.4, 1] }, { duration: 0.45, delay: 0.25, amount: 0.5 });
    const now = $('.rd-now', root);
    if (now) play([now], { scale: ['1 0', '1 1'] }, { duration: 0.7, delay: 0.2, easing: EASE_IO });
  },
  /* 数字：首次进入页面从 0 滚动；刷新时只对变化的数字从旧值滚到新值并闪一下 */
  counts(root, prev, entering) {
    $$('[data-k][data-v]', root).forEach((el) => {
      const k = el.dataset.k, to = +el.dataset.v, d = +el.dataset.d || 0;
      const had = prev && Object.prototype.hasOwnProperty.call(prev, k);
      const from = had ? prev[k] : (entering ? 0 : to);
      if (from === to) return;
      if (had) {
        el.classList.remove('bump');
        void el.offsetWidth;
        el.classList.add('bump');
      }
      if (!canMove()) return;
      tween(from, to, had ? 800 : 1100, (v) => { el.textContent = fmtN(d ? v : Math.round(v), d); });
    });
  },
  snapshot(root) {
    const m = {};
    $$('[data-k][data-v]', root).forEach((el) => { m[el.dataset.k] = +el.dataset.v; });
    return m;
  },
  drawer(root) {
    if (!canMove()) return;
    const secs = Array.from(root.children);
    play(secs, { opacity: [0, 1], translate: ['0 8px', '0 0'] }, { duration: 0.45, delay: 0.05, amount: Math.min(0.3, secs.length * 0.03) });
  },
  fade(el, ms = 200) { if (canMove()) el.animate({ opacity: [0, 1] }, { duration: ms, easing: 'ease-out' }); },
};
/* 数值补间：ease-out（二次），结束时落到准确值 */
function tween(from, to, ms, onUpdate) {
  const t0 = performance.now();
  const step = (t) => {
    const p = Math.min(1, (t - t0) / ms);
    const e = 1 - (1 - p) * (1 - p);
    onUpdate(p < 1 ? from + (to - from) * e : to);
    if (p < 1) requestAnimationFrame(step);
  };
  onUpdate(from);
  requestAnimationFrame(step);
}

/* ---------- 图表（ECharts） ---------- */
const EC = { specs: [], live: [] };
const hasEC = () => !!window.echarts;
const ro = window.ResizeObserver ? new ResizeObserver((entries) => {
  for (const e of entries) {
    const inst = window.echarts && window.echarts.getInstanceByDom(e.target);
    if (inst) inst.resize();
  }
}) : null;
function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function theme() {
  return {
    ink: css('--ink'), ink2: css('--ink-2'), ink3: css('--ink-3'), line: css('--line'), line2: css('--line-2'),
    surface: css('--surface'), chart: css('--chart'), font: css('--font'),
    ok: css('--ok'), bad: css('--bad'), q: css('--q'), warn: css('--warn'),
    p: Object.fromEntries(PLAT_ORDER.map((k) => [k, css('--p-' + k)])),
  };
}
const colorOf = (pk, t) => (pk && t.p[pk]) || t.chart;
function chart(build, h, cls = '') {
  const id = 'ec' + Math.random().toString(36).slice(2, 9);
  EC.specs.push({ id, build });
  return `<div class="ec ${cls}" data-ec="${id}" style="height:${h}px"></div>`;
}
function baseOpt(t, animate) {
  return {
    animation: animate && !RM.matches,
    animationDuration: 800, animationEasing: 'cubicOut', animationDurationUpdate: 500,
    textStyle: { fontFamily: t.font, color: t.ink3, fontSize: 11 },
    tooltip: {
      trigger: 'axis', confine: true, backgroundColor: t.ink, borderWidth: 0, padding: [7, 10],
      textStyle: { color: t.surface, fontSize: 12, fontFamily: t.font },
      extraCssText: 'border-radius:7px;box-shadow:none;', axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(127,127,127,.08)' } },
    },
  };
}
function mountCharts(root, animate) {
  const specs = EC.specs;
  EC.specs = [];
  for (const s of specs) {
    const el = root.querySelector(`[data-ec="${s.id}"]`);
    if (!el) continue;
    if (!hasEC()) { el.innerHTML = '<div class="ec-fallback">图表组件没有加载，数据见下方表格</div>'; continue; }
    try {
      const inst = window.echarts.init(el, null, { renderer: 'canvas' });
      const t = theme();
      const base = baseOpt(t, animate), own = s.build(t);
      // tooltip 要合并，不然各图自己的 formatter 会把统一的深色提示框样式整个覆盖掉
      inst.setOption({ ...base, ...own, tooltip: { ...base.tooltip, ...(own.tooltip || {}) } });
      EC.live.push(inst);
      if (ro) ro.observe(el);
    } catch (e) {
      console.error(e);
    }
  }
}
function disposeCharts(scope) {
  EC.live = EC.live.filter((inst) => {
    const dom = inst.getDom();
    if (!dom || !dom.isConnected || (scope && scope.contains(dom))) {
      if (ro && dom) ro.unobserve(dom);
      inst.dispose();
      return false;
    }
    return true;
  });
}
const tipFmt = (tips) => (ps) => esc(tips[(Array.isArray(ps) ? ps[0] : ps).dataIndex] || '');
/* 柱状图：单系列，颜色跟着平台或主色走 */
function barChart({ labels, values, tips, color, pk, horizontal = false, yName = '' }) {
  return (t) => {
    const c = color || colorOf(pk, t);
    const cat = { type: 'category', data: labels, axisLine: { lineStyle: { color: t.line2 } }, axisTick: { show: false }, axisLabel: { color: t.ink3, fontSize: 11, hideOverlap: true } };
    const val = { type: 'value', name: yName, minInterval: 1, splitNumber: 3, axisLabel: { color: t.ink3, fontSize: 11 }, splitLine: { lineStyle: { color: t.line, type: [3, 3] } } };
    return {
      grid: horizontal ? { left: 8, right: 44, top: 6, bottom: 6, containLabel: true } : { left: 6, right: 8, top: 14, bottom: 4, containLabel: true },
      tooltip: { formatter: tipFmt(tips) },
      xAxis: horizontal ? { ...val, splitLine: { show: false }, axisLabel: { show: false } } : cat,
      yAxis: horizontal ? { ...cat, inverse: true, axisLine: { show: false }, axisLabel: { color: t.ink2, fontSize: 12, width: 90, overflow: 'truncate' } } : val,
      series: [{
        type: 'bar', data: values, barMaxWidth: horizontal ? 16 : 22, barCategoryGap: '30%',
        itemStyle: { color: c, borderRadius: horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0] },
        emphasis: { itemStyle: { opacity: 0.85 } },
        label: horizontal ? { show: true, position: 'right', color: t.ink2, fontSize: 12, fontWeight: 600, formatter: (p) => fmtN(p.value, 0) } : { show: false },
        animationDelay: (i) => i * 35,
      }],
    };
  };
}
function lineChart({ labels, values, tips, color, pk, area = true }) {
  return (t) => {
    const c = color || colorOf(pk, t);
    return {
      grid: { left: 6, right: 12, top: 14, bottom: 4, containLabel: true },
      tooltip: { formatter: tipFmt(tips), axisPointer: { type: 'line', lineStyle: { color: t.line2 } } },
      xAxis: { type: 'category', data: labels, boundaryGap: false, axisLine: { lineStyle: { color: t.line2 } }, axisTick: { show: false }, axisLabel: { color: t.ink3, fontSize: 11, hideOverlap: true } },
      yAxis: { type: 'value', scale: true, splitNumber: 3, axisLabel: { color: t.ink3, fontSize: 11 }, splitLine: { lineStyle: { color: t.line, type: [3, 3] } } },
      series: [{
        type: 'line', data: values, smooth: 0.25, symbol: 'circle', symbolSize: 6, showSymbol: values.length < 20,
        lineStyle: { width: 2, color: c }, itemStyle: { color: c, borderColor: t.surface, borderWidth: 1.5 },
        areaStyle: area ? { color: new window.echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: c + '33' }, { offset: 1, color: c + '00' }]) } : undefined,
      }],
    };
  };
}
function sparkChart(points, pk) {
  return (t) => {
    const c = colorOf(pk, t);
    return {
      grid: { left: 3, right: 5, top: 5, bottom: 5 },
      tooltip: { formatter: tipFmt(points.map((p) => `${p.day}：${fmtN(p.n, 0)} 粉丝`)), axisPointer: { type: 'line', lineStyle: { color: t.line2 } } },
      xAxis: { type: 'category', show: false, data: points.map((p) => p.day), boundaryGap: false },
      yAxis: { type: 'value', show: false, scale: true },
      series: [{ type: 'line', data: points.map((p) => p.n), smooth: 0.3, symbol: 'circle', symbolSize: 5, showSymbol: false, lineStyle: { width: 2, color: c }, itemStyle: { color: c }, endLabel: { show: false } }],
    };
  };
}

/* 每天的发布结果：已发/失败/排队堆叠柱 + 成功率折线（右轴） */
function pubChart({ days, rows }) {
  return (t) => {
    const ax = { axisLine: { lineStyle: { color: t.line2 } }, axisTick: { show: false }, axisLabel: { color: t.ink3, fontSize: 11, hideOverlap: true } };
    const tips = rows.map((r) => `${r.day}\n应发 ${r.expected}，已发 ${r.done}，失败 ${r.fail}，排队 ${r.queue}\n提交尝试 ${r.attempts} 次${isNum(r.rate) ? `，成功率 ${pct(r.rate)}` : ''}`);
    return {
      grid: { left: 6, right: 8, top: 30, bottom: 4, containLabel: true },
      legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 10, icon: 'roundRect', textStyle: { color: t.ink2, fontSize: 11 } },
      tooltip: { formatter: tipFmt(tips), extraCssText: 'border-radius:7px;box-shadow:none;white-space:pre-line;' },
      xAxis: { type: 'category', data: days.map((d) => +d.slice(8, 10) + '日'), ...ax },
      yAxis: [
        { type: 'value', minInterval: 1, splitNumber: 3, axisLabel: { color: t.ink3, fontSize: 11 }, splitLine: { lineStyle: { color: t.line, type: [3, 3] } } },
        { type: 'value', min: 0, max: 1, splitNumber: 2, axisLabel: { color: t.ink3, fontSize: 11, formatter: (v) => Math.round(v * 100) + '%' }, splitLine: { show: false } },
      ],
      series: [
        { name: '已发', type: 'bar', stack: 'p', data: rows.map((r) => r.done), itemStyle: { color: t.ok }, barMaxWidth: 16 },
        { name: '失败', type: 'bar', stack: 'p', data: rows.map((r) => r.fail), itemStyle: { color: t.bad } },
        { name: '排队', type: 'bar', stack: 'p', data: rows.map((r) => r.queue), itemStyle: { color: t.q, borderRadius: [3, 3, 0, 0] } },
        { name: '成功率', type: 'line', yAxisIndex: 1, data: rows.map((r) => r.rate), connectNulls: true, smooth: 0.2, symbol: 'circle', symbolSize: 5, lineStyle: { width: 2, color: t.ink2 }, itemStyle: { color: t.ink2 } },
      ],
    };
  };
}

/* ---------- 路由 ---------- */
function parseHash() {
  const h = location.hash.replace(/^#\/?/, '');
  const [p, qs] = h.split('?');
  const parts = (p || '').split('/').filter(Boolean);
  const page = PAGES.some((x) => x.id === parts[0]) ? parts[0] : 'overview';
  return { page, arg: parts[1] ? decodeURIComponent(parts[1]) : null, q: Object.fromEntries(new URLSearchParams(qs || '')) };
}
function hashOf(page, arg, q) {
  const h = '#/' + page + (arg ? '/' + encodeURIComponent(arg) : '');
  const qs = new URLSearchParams(Object.entries(q || {}).filter(([, v]) => v !== undefined && v !== null && v !== '')).toString();
  return qs ? h + '?' + qs : h;
}
function go(page, arg, q) {
  const { item, ...rest } = q || {}; // 打开的抽屉不跟着换页带走
  const h = hashOf(page, arg, rest);
  if (location.hash === h) load(true);
  else location.hash = h;
}
function setQ(patch) { const r = S.route; go(r.page, r.arg, { ...r.q, ...patch }); }
/* 抽屉打开的条目写进地址（可收藏、可分享、刷新后还在），不触发换页 */
function syncItemParam(id) {
  const r = S.route;
  const q = { ...r.q };
  if (id) q.item = id; else delete q.item;
  r.q = q;
  const h = hashOf(r.page, r.arg, q);
  if (location.hash !== h) history.replaceState(null, '', h);
}

/* ---------- 骨架屏 ---------- */
function skeleton(page) {
  const blk = (h, extra = '') => `<div class="sk" style="height:${h}px;${extra}"></div>`;
  const row = (n, h, min = 180) => `<div class="sk-row" style="grid-template-columns:repeat(auto-fill,minmax(${min}px,1fr))">${Array.from({ length: n }, () => blk(h)).join('')}</div>`;
  if (page === 'overview') return `<div class="sk-wrap"><div class="sk-row" style="grid-template-columns:repeat(auto-fit,minmax(320px,1fr))">${blk(330)}${blk(330)}</div>${blk(120)}${row(5, 150, 200)}${blk(380)}</div>`;
  if (page === 'content') return `<div class="sk-wrap">${blk(30, 'width:60%')}${row(10, 330, 196)}</div>`;
  if (page === 'data') return `<div class="sk-wrap">${row(4, 90, 160)}${row(5, 160, 200)}<div class="sk-row" style="grid-template-columns:1fr 1fr">${blk(220)}${blk(220)}</div>${blk(260)}</div>`;
  if (page === 'accounts' || page === 'reports') return `<div class="sk-wrap"><div class="sk-row" style="grid-template-columns:240px 1fr">${blk(420)}<div class="sk-wrap">${blk(180)}${row(4, 80, 160)}${blk(240)}</div></div></div>`;
  if (page === 'growth') return `<div class="sk-wrap">${blk(30, 'width:40%')}${row(5, 90, 160)}<div class="sk-row" style="grid-template-columns:2fr 1fr">${blk(280)}${blk(280)}</div>${blk(360)}</div>`;
  if (page === 'calendar') return `<div class="sk-wrap">${blk(30, 'width:50%')}${blk(300)}${blk(420)}</div>`;
  return `<div class="sk-wrap">${blk(80)}${row(3, 140, 260)}${blk(320)}</div>`;
}

/* ---------- 页面：总览 ---------- */
function stackbar(c, thin) {
  const parts = [['done', c.done], ['queue', c.queue], ['fail', c.fail], ['warn', c.warn]];
  const sum = parts.reduce((a, [, v]) => a + (v || 0), 0);
  const den = Math.max(c.expected || 0, sum, 1);
  const segs = parts.filter(([, v]) => v > 0).map(([k, v]) => `<i class="s-${k}" style="width:${((v / den) * 100).toFixed(2)}%"></i>`).join('');
  const tip = `应发 ${c.expected}，已发 ${c.done}，排队 ${c.queue}，失败 ${c.fail}${c.warn ? `，待核实 ${c.warn}` : ''}`;
  return `<div class="stackbar${thin ? ' thin' : ''}" data-tip="${esc(tip)}" role="img" aria-label="${esc(tip)}">${segs}</div>`;
}
const cls = (v) => (!isNum(v) ? 'none' : v > 0 ? 'up' : v < 0 ? 'down' : '');
const sign = (v) => (!isNum(v) ? '—' : v > 0 ? '+' + fmtN(v, 0) : v < 0 ? '−' + fmtN(-v, 0) : '0');

function renderOverview(d) {
  updateBadge(d.pending.length);
  paintBrand(d.accounts);
  const uniq = d.accounts.filter((a) => !a.shared_with);
  const maxFans = Math.max(1, ...uniq.map((a) => a.fans || 0));
  const mix = [...uniq].sort((a, b) => (b.fans || 0) - (a.fans || 0)).map((a) => `
    <div class="mix-row" data-tip="${esc(`${a.name}（${a.platform}）：${fmtN(a.fans, 0)} 粉丝`)}">
      ${logo(a.pkey)}<span class="nm">${esc(a.name)}</span>${bar((a.fans || 0) / maxFans)}
      <span class="v">${cnt('fans:' + a.slot, a.fans)}</span></div>`).join('');
  const hist = d.fans_history_records || 0;
  const p = d.publish;
  const pubRows = d.accounts.map((a) => `
    <div class="pub-row">${logo(a.pkey)}<span class="nm">${esc(a.name)}</span>${stackbar(a, true)}
      <span class="v num">${cnt('done:' + a.slot, a.done)}<span class="muted">/${a.expected}</span></span></div>`).join('');
  const d7 = d.fans_d7_span > 1
    ? `<div class="hero-stat"><div class="k">较 ${d.fans_d7_span >= 7 ? 7 : d.fans_d7_span} 天前</div><div class="v ${cls(d.fans_d7)}">${sign(d.fans_d7)}</div></div>`
    : `<div class="hero-stat" data-tip="粉丝历史满 2 天后才有这一项"><div class="k">较 7 天前</div><div class="v none">—</div></div>`;
  const hero = `
  <div class="hero">
    <section class="panel hero-fans" aria-label="粉丝">
      <div class="hero-label">粉丝总数<span class="muted small">北极星指标：涨粉</span><span class="right">采集于 ${esc(mdShort(d.fans_updated))} ${esc(hm(d.fans_updated))}</span></div>
      <div class="hero-num">${cnt('fans_total', d.fans_total)}</div>
      <div class="hero-stats">
        <div class="hero-stat"><div class="k">较昨日</div><div class="v ${cls(d.fans_d1)}">${sign(d.fans_d1)}</div></div>
        ${d7}
        <div class="hero-stat"><div class="k">近 7 天播放/阅读</div><div class="v">${cnt('views7', d.views7_total)}</div></div>
        <div class="hero-stat"><div class="k">近 7 天作品</div><div class="v">${cnt('posts7', d.posts7_total)}</div></div>
      </div>
      ${S.meta && S.meta.goal ? `<div class="hero-goal">${goalBlock(S.meta.goal, d.fans_total, isNum(d.fans_d7) && d.fans_d7_span > 1 ? d.fans_d7 / Math.min(7, d.fans_d7_span) : null)}</div>` : ''}
      <div class="mix">${mix}</div>
      ${hist < 2 ? `<div class="hero-note">粉丝历史目前 ${hist} 条，每天采集后，较昨日、较 7 天和走势会逐步完整。</div>` : ''}
    </section>
    <section class="panel hero-pub" aria-label="今日发布">
      <div class="hero-label">今日发布<span class="muted small">配额是下限，发多了正常</span><span class="right">${esc(dayLabel(d.today))}</span></div>
      <div class="pub-frac"><span class="a">${cnt('pub_done', p.done)}</span><span class="b">/ ${p.expected} 应发</span></div>
      ${stackbar(p)}
      <div class="legend">
        <span class="k"><span class="sw sw-done"></span>已发 <b>${cnt('pub_done2', p.done)}</b></span>
        <span class="k"><span class="sw sw-queue"></span>排队 <b>${cnt('pub_queue', p.queue)}</b></span>
        <span class="k"><span class="sw sw-fail"></span>失败 <b>${cnt('pub_fail', p.fail)}</b></span>
        ${p.warn ? `<span class="k"><span class="sw sw-warn"></span>待核实 <b>${cnt('pub_warn', p.warn)}</b></span>` : ''}
        <span class="k"><span class="sw sw-rest"></span>未排</span>
      </div>
      <div class="pub-rows">${pubRows}</div>
    </section>
  </div>`;

  const alertRow = (r, resolved) => `
    <div class="alert-row" data-pid="${esc(r.id)}">
      <div class="wk">${pill(r.bucket === 'queue' ? 'warn' : r.bucket, r.kind_label)}<div class="t num">${esc(mdShort(r.day))} ${esc(r.time)}</div></div>
      <div class="wh">${who(r.pkey, r.account_name)}</div>
      <div class="bd"><div class="title">${esc(r.title || '（无标题）')}</div>
        <div class="why">${r.reason && !resolved ? `<span class="rtag">${esc(r.reason.label)}</span>` : ''}${r.attempts > 1 ? `<b>同一条共 ${r.attempts} 次尝试</b>，最新一次：` : ''}${esc(resolved ? r.resolved_reason + '。' + (r.detail_text || '') : r.detail_text || r.status_label)}</div>
        ${r.reason && !resolved ? `<div class="fix">${ico('bolt')}<span>${esc(r.reason.hint)}</span></div>` : ''}</div>
      <div class="act"><button class="btn" type="button" data-item="${esc(r.id)}">查看</button></div>
    </div>`;
  const resolvedBlock = d.resolved.length
    ? `<details class="resolved" data-k-open="ov-resolved"><summary>另有 ${d.resolved.length} 条已处理：已重新提交，或备注说明已处理</summary>${d.resolved.map((r) => alertRow(r, true)).join('')}</details>` : '';
  const rsum = {};
  d.pending.forEach((r) => { if (r.reason) rsum[r.reason.label] = (rsum[r.reason.label] || 0) + 1; });
  const pending = d.pending.length
    ? `<section class="panel alert sec" aria-label="待处理">
        <div class="panel-h"><h2>待处理 ${cnt('pending_n', d.pending.length)}</h2><span class="meta">近 3 天发布失败、待核实，以及今天到点还没提交的条目${d.pending_items > d.pending.length ? `（${d.pending_items} 条台账记录，同一内容的多次尝试已合并）` : ''}</span>
          <span class="right">${Object.entries(rsum).map(([k, v]) => `<span class="rtag">${esc(k)} ${v}</span>`).join('')}<a href="#/calendar">失败原因统计</a></span></div>
        ${d.pending.map((r) => alertRow(r)).join('')}${resolvedBlock}</section>`
    : `<section class="panel sec"><div class="alert-ok"><span class="g">✓</span>没有待处理事项。近 3 天没有失败或待核实的发布。</div>${resolvedBlock}</section>`;

  const cards = d.accounts.map((a) => {
    const sp = a.spark || [];
    const sparkHtml = sp.length >= 2 ? chart(sparkChart(sp, a.pkey), 36) : `<div class="spark-empty" title="粉丝历史满 2 天后显示走势">${sp.length ? '' : '还没有粉丝记录'}</div>`;
    const fansLine = a.shared_with
      ? `<span class="n">${cnt('cf:' + a.slot, a.fans)}</span><span class="u">与「${esc(a.shared_with)}」同一个号</span>`
      : `<span class="n">${cnt('cf:' + a.slot, a.fans)}</span><span class="u">粉丝</span>${delta(a.d1, '昨日')}${a.d7_span > 1 ? delta(a.d7, `${a.d7_span}天`) : ''}`;
    return `
    <button class="acc lift" type="button" data-go="accounts/${esc(a.slot)}" aria-label="${esc(a.name)} 账号详情">
      <div class="acc-top" title="${esc(a.name)}（${esc(a.platform)}）">${who(a.pkey, a.name)}<span class="frac">今日 <b class="num">${a.done}</b>/${a.expected}</span></div>
      <div class="acc-fans">${fansLine}</div>
      ${sparkHtml}
      <div class="acc-foot"><span>近 7 天作品 <b class="num">${a.posts7}</b></span><span>均播放 <b class="num">${fmtN(a.views7_avg, 0)}</b></span></div>
    </button>`;
  }).join('');

  const hot = d.hot;
  const fresh = hotFreshness(hot ? hot.top : []);
  const hotPanel = `
    <section class="panel" aria-label="热点">
      <div class="panel-h"><h2>热点前五</h2><span class="meta">${hot ? `雷达 ${esc(mdShort(hot.at))} ${esc(hm(hot.at))}，新 ${fmtN(hot.new, 0)} / 共 ${fmtN(hot.total, 0)}` : ''}</span>
        <span class="right"><a href="#/hot">全部候选</a></span></div>
      ${hot && hot.top.length ? `<ol class="list" data-stagger>${hot.top.map((c, i) => `
        <li class="li hot-li${fresh.has(c.title) ? ' is-new' : ''}"><span class="rk num">${i + 1}</span>
          <div><div class="tt">${esc(c.title)} ${fresh.has(c.title) ? '<span class="tag new">新上榜</span>' : ''}</div>${c.angle ? `<div class="an clamp2">${esc(c.angle)}</div>` : ''}
            <div class="srcs">${(c.sources || []).slice(0, 4).map((s) => `<span class="src">${esc(s)}</span>`).join('')}</div></div>
          <div class="sc num" data-tip="综合分 ${esc(fmtN(c.score, 2))}，跨平台热度 ${esc(fmtN(c.cross_score, 1))}">${fmtN(c.score, 1)}<small>跨平台 ${fmtN(c.cross_score, 0)}</small></div></li>`).join('')}</ol>`
        : empty('今天还没有雷达结果。雷达在 07:00–23:30 每 30 分钟扫描一次，结果写在 days/&lt;日期&gt;/radar/。')}
    </section>`;
  const runs = d.runs || [];
  const runsPanel = `
    <section class="panel" aria-label="今日任务">
      <div class="panel-h"><h2>今日任务运行</h2><span class="meta">${runs.length ? `${runs.length} 次` : ''}</span><span class="right"><a href="#/plan?tab=runs">近 7 天</a></span></div>
      ${runs.length ? `<ul class="list" data-stagger>${runs.slice(0, 8).map(runLi).join('')}</ul>`
        : empty('今天还没有任务运行记录。定时任务开工和收工时会写进 days/&lt;今天&gt;/runs.jsonl，写入后这里自动出现。')}
    </section>`;
  const e = d.engagement;
  const engRows = e ? e.platforms.filter((x) => x.comment && (x.comment.cap > 0 || x.comment.used > 0)).map((x) => meterRow(x.pkey, '评论', x.comment.used, x.comment.cap)).join('') : '';
  const engPanel = `
    <section class="panel" aria-label="今日互动">
      <div class="panel-h"><h2>今日互动</h2><span class="meta">${e ? `共 ${e.total} 次，评论 ${e.by_action.comment || 0}，回复 ${e.by_action.reply || 0}，点赞 ${e.by_action.like || 0}` : ''}</span>
        <span class="right"><a href="#/engagement">流水</a></span></div>
      <div class="panel-b">${e ? engRows || empty('今天各平台评论额度都还没用。') : empty('互动记录读取失败。')}</div>
    </section>`;
  const m = d.manual;
  const manualPanel = `
    <section class="panel" aria-label="运营手册">
      <div class="panel-h"><h2>运营手册</h2><span class="right"><a href="#/plan?tab=changelog">全部版本</a></span></div>
      <div class="panel-b">
        ${m.exists ? `<div class="ver num">${esc(m.version || '未标版本')}</div><div class="muted small">00-必读.md 更新于 ${esc(mdShort(m.updated))} ${esc(hm(m.updated))}</div>`
          : `<div class="ver muted">尚未建立</div><div class="muted small">运营手册/00-必读.md 还不存在</div>`}
        <div style="margin-top:14px">${(m.changes || []).length ? `<ol class="tl compact">${m.changes.slice(0, 4).map((c, i) => `
          <li class="tl-item${i === 0 ? ' cur' : ''}"><span class="tl-dot"></span><div class="tl-h"><span class="tl-v num">${esc(c.version || c.title)}</span>${c.when ? `<span class="tl-when num">${esc(c.when.slice(5))}</span>` : ''}${c.source ? `<span class="tl-src ${SRC_CLS[c.source] || ''}">${esc(c.source)}</span>` : ''}</div><div class="tl-sum clamp2">${esc(c.summary || '')}</div></li>`).join('')}</ol>`
          : `<div class="muted small">${m.changelog_exists ? '变更日志里还没有条目。' : '变更日志尚未建立。'}</div>`}</div>
      </div>
    </section>`;

  return `${errNote(d.errors)}${hero}${pending}
    <div class="sec"><div class="sec-h"><h2>账号</h2><span class="meta">${d.accounts.length} 个发布位，点卡片看详情；粉丝历史满 2 天后卡片里画走势</span></div>
      <div class="acc-grid" data-stagger style="--n:${balancedCols(d.accounts.length)}">${cards}</div></div>
    ${rundown(d)}
    <div class="sec grid cols-3">${hotPanel}<div class="grid" style="align-content:start">${runsPanel}${engPanel}</div>${manualPanel}</div>`;
}
const balancedCols = (count, max = 5) => (count <= max ? count : Math.ceil(count / Math.ceil(count / max)));
/* 热点「新上榜」：记住每个标题第一次出现的时间，2 小时内标新 */
function hotFreshness(list) {
  const seen = store.get('hot.seen', null);
  const nowT = Date.now();
  const map = seen || {};
  const fresh = new Set();
  for (const c of list) {
    if (!Object.prototype.hasOwnProperty.call(map, c.title)) map[c.title] = seen ? nowT : 0;
    if (map[c.title] && nowT - map[c.title] < 2 * 3600e3) fresh.add(c.title);
  }
  const keep = Object.fromEntries(Object.entries(map).filter(([, t]) => t === 0 || nowT - t < 3 * 864e5).slice(-400));
  store.set('hot.seen', keep);
  return fresh;
}
function meterRow(pk, label, used, cap) {
  const r = cap > 0 ? used / cap : 0;
  const c = cap > 0 && used >= cap ? 'max' : r >= 0.8 ? 'hi' : '';
  return `<div class="meter">${logo(pk)}<span class="ink2">${esc(label)}</span>${bar(cap > 0 ? r : used ? 1 : 0, c, `${label} ${used}/${cap > 0 ? cap : '不限'}`)}
    <span class="v num"><b>${used}</b>/${cap > 0 ? cap : '不限'}</span></div>`;
}
function runLi(r) {
  const st = r.state === 'done' ? pill('done', '已收工') : r.state === 'running' ? pill('queue', '进行中') : pill('warn', '未收工');
  const t = `${r.start ? hm(r.start) : '?'}${r.end ? '–' + hm(r.end) : ''}${isNum(r.minutes) ? `，${r.minutes} 分钟` : ''}`;
  return `<li class="li run-li"><div><span class="tk">${esc(r.task)}</span> <span class="tm num">${esc(t)}</span>${r.version ? ` <span class="tm">手册 ${esc(r.version)}</span>` : ''}</div>
    <div>${st}</div>${r.summary ? `<div class="sm clamp2">${esc(r.summary)}</div>` : ''}</li>`;
}
function rundown(d) {
  const toMin = (t) => { const mm = /^(\d{1,2}):(\d{2})/.exec(t || ''); return mm ? +mm[1] * 60 + +mm[2] : null; };
  const nowMin = toMin(hm(d.now));
  const ticks = [0, 3, 6, 9, 12, 15, 18, 21, 24];
  const pctOf = (min) => ((min / 1440) * 100).toFixed(3) + '%';
  const bySlot = {};
  for (const t of d.timeline) (bySlot[t.slot] = bySlot[t.slot] || []).push(t);
  const rows = d.accounts.map((a) => {
    const its = (bySlot[a.slot] || []).filter((t) => toMin(t.time) !== null).sort((x, y) => toMin(x.time) - toMin(y.time));
    let lastMin = -999, flip = 0;
    const marks = its.map((t) => {
      const mm = toMin(t.time);
      let dy = 0;
      if (mm - lastMin < 22) { flip = flip ? 0 : 1; dy = flip ? -9 : 9; } else flip = 0;
      lastMin = mm;
      const kind = t.superseded_by ? 'ghost' : t.bucket;
      const g = kind === 'done' ? '✓' : kind === 'fail' ? '✕' : kind === 'warn' ? '<span>!</span>' : kind === 'ghost' ? '×' : '';
      const tip = `${t.time} ${t.account_name || a.name}\n${t.title || ''}\n${t.status_label}${t.superseded_by ? '，已由重提的条目替代' : ''}`;
      return `<button type="button" class="rd-mk ${kind}" style="left:${pctOf(mm)};${dy ? `margin-top:${dy - 7}px` : ''}" data-item="${esc(t.id)}" data-tip="${esc(tip)}" aria-label="${esc(tip)}">${g}</button>`;
    }).join('');
    const plans = (d.planned[a.slot] || []).map((t) => `<span class="rd-plan" style="left:${pctOf(toMin(t))}" data-tip="${esc(`计划时段 ${t}`)}"></span>`).join('');
    const grid = ticks.slice(1, -1).map((h) => `<span class="rd-grid" style="left:${pctOf(h * 60)}"></span>`).join('');
    return `<div class="rd-row"><div class="rd-lab">${logo(a.pkey)}<span class="nm">${esc(a.name)}</span><span class="c num">${a.done}/${a.expected}</span></div>
      <div class="rd-track">${grid}${plans}${marks}</div></div>`;
  }).join('');
  const axis = `<div class="rd-axis"><div></div><div class="ticks">${ticks.map((h) => `<span class="tk num" style="left:${pctOf(h * 60)}">${String(h).padStart(2, '0')}:00</span>`).join('')}</div></div>`;
  const now = nowMin !== null ? `<div class="rd-now-layer"><div class="rd-now" style="left:${pctOf(nowMin)}"><span class="num">现在 ${esc(hm(d.now))}</span></div></div>` : '';
  const legend = `<div class="rd-legend">
    <span class="k"><span class="rd-mk done">✓</span>已发</span><span class="k"><span class="rd-mk queue"></span>排队</span>
    <span class="k"><span class="rd-mk fail">✕</span>失败</span><span class="k"><span class="rd-mk warn"><span>!</span></span>待核实</span>
    <span class="k"><span class="rd-mk ghost">×</span>已被重提替代</span><span class="k"><span class="rd-plan"></span>计划时段</span></div>`;
  return `<section class="panel sec" aria-label="今日排期" data-rundown>
    <div class="panel-h"><h2>今日排期</h2><span class="meta">${esc(dayLabel(d.today))}，点圆点看详情</span><span class="right">${legend}</span></div>
    <div class="rundown-wrap" data-keep-scroll="rundown"><div class="rundown">${axis}${rows}${now}</div></div></section>`;
}

/* ---------- 通用：可排序表格 ---------- */
function sortRows(rows, key, def, textCols = []) {
  const s = S.ui.sort[key] || def;
  const val = (x) => (typeof s.k === 'function' ? s.k(x) : x[s.k]);
  return [...rows].sort((a, b) => {
    const va = val(a), vb = val(b);
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    return (va > vb ? 1 : va < vb ? -1 : 0) * s.dir;
  });
}
function th(key, col, label, cls = '', def = null) {
  const s = S.ui.sort[key] || def || {};
  return `<th class="sort ${cls}" data-sort="${esc(key)}:${esc(col)}" ${s.k === col ? `aria-sort="${s.dir > 0 ? 'ascending' : 'descending'}"` : ''} tabindex="0">${label}</th>`;
}
const TEXT_COLS = new Set(['title', 'platform_name', 'name', 'mode', 'key']);
function sortBy(spec) {
  const [key, col] = spec.includes(':') ? spec.split(':') : ['posts', spec];
  const s = S.ui.sort[key] || (key === 'posts' ? { k: 'created', dir: -1 } : {});
  S.ui.sort[key] = s.k === col ? { k: col, dir: -s.dir } : { k: col, dir: TEXT_COLS.has(col) ? 1 : -1 };
  rerender();
}

/* ---------- 页面：增长 ---------- */
/* 近 N 天日均净增：取序列里最后 N+1 个有值的点 */
function perDay(series, n = 7) {
  const pts = series.map((v, i) => [i, v]).filter(([, v]) => isNum(v));
  if (pts.length < 2) return null;
  const tail = pts.slice(-(n + 1));
  const [i0, v0] = tail[0], [i1, v1] = tail[tail.length - 1];
  return i1 > i0 ? (v1 - v0) / (i1 - i0) : null;
}
function goalBlock(goal, cur, pd) {
  if (!goal || !isNum(goal.fans) || !isNum(cur)) return '';
  const left = goal.fans - cur;
  const r = Math.max(0, Math.min(1, cur / goal.fans));
  const daysLeft = goal.by ? daysBetween(todayStr(), goal.by) : null;
  const need = daysLeft > 0 && left > 0 ? left / daysLeft : null;
  const eta = isNum(pd) && pd > 0 && left > 0 ? Math.ceil(left / pd) : null;
  const onTrack = need != null && isNum(pd) ? pd >= need : null;
  return `<div class="goal">
    <div class="goal-h"><span class="k">${esc(goal.label || `目标 ${fmtN(goal.fans, 0)} 粉`)}${goal.by ? `<span class="muted">，截止 ${esc(goal.by)}</span>` : ''}</span>
      <span class="v num">${fmtN(cur, 0)} <span class="muted">/ ${fmtN(goal.fans, 0)}</span></span></div>
    <div class="goal-bar" role="progressbar" aria-valuemin="0" aria-valuemax="${goal.fans}" aria-valuenow="${cur}"><i style="width:${(r * 100).toFixed(1)}%"></i></div>
    <div class="goal-f">${left <= 0 ? '<b>已达成</b>' : `<span>还差 <b class="num">${fmtN(left, 0)}</b></span>`}
      ${daysLeft != null && left > 0 ? `<span>剩 ${daysLeft} 天${need ? `，需要日均 <b class="num">+${fmtN(need, 1)}</b>` : ''}</span>` : ''}
      ${isNum(pd) ? `<span>近 7 天日均 <b class="num">${pd >= 0 ? '+' : '−'}${fmtN(Math.abs(pd), 1)}</b>${eta ? `，照这个速度约 ${fmtN(eta, 0)} 天达成` : ''}</span>` : ''}
      ${onTrack != null && left > 0 ? pill(onTrack ? 'done' : 'warn', onTrack ? '进度正常' : '落后于目标') : ''}</div></div>`;
}
/* 根据数据自动写几条大白话结论，没有足够数据就不写 */
function growthInsights(d) {
  const out = [];
  const roi = d.roi.filter((r) => !r.shared_with);
  const withGain = roi.filter((r) => isNum(r.gain));
  const total = withGain.reduce((a, r) => a + Math.max(0, r.gain), 0);
  if (d.history_records < 3) out.push(['warn', `粉丝历史只有 ${d.history_records} 天，涨粉相关的结论先别下，攒够一周再看。`]);
  if (withGain.length && total > 0) {
    const top = [...withGain].sort((a, b) => b.gain - a.gain)[0];
    out.push(['ok', `「${top.name}」（${top.platform}）净增最多：+${fmtN(top.gain, 0)}，占全矩阵净增的 ${pct(top.gain / total)}。`]);
  }
  const best = roi.filter((r) => isNum(r.gain_per_post) && r.posts >= 3).sort((a, b) => b.gain_per_post - a.gain_per_post)[0];
  if (best) out.push(['ok', `每条内容带来粉丝最多的是「${best.name}」（${best.platform}）：平均每条 +${fmtN(best.gain_per_post, 1)}。`]);
  roi.filter((r) => r.posts >= 5 && isNum(r.gain) && r.gain <= 0).forEach((r) => {
    out.push(['bad', `「${r.name}」（${r.platform}）发了 ${r.posts} 条，粉丝${r.gain < 0 ? `少了 ${-r.gain}` : '没涨'}：检查主页简介、置顶和内容里的关注理由。`]);
  });
  roi.filter((r) => r.expected >= 5 && r.posts / r.expected < 0.6).forEach((r) => {
    out.push(['warn', `「${r.name}」（${r.platform}）只发出应发的 ${pct(r.posts / r.expected)}（${r.posts}/${r.expected}），失败 ${r.fails} 条。`]);
  });
  const rate = d.publish_daily.filter((x) => isNum(x.rate));
  if (rate.length >= 3) {
    const avg = rate.reduce((a, x) => a + x.rate, 0) / rate.length;
    if (avg < 0.85) out.push(['bad', `近 ${rate.length} 天平均发布成功率 ${pct(avg)}，低于 85%。先看「日历」页的失败原因。`]);
  }
  return out.slice(0, 6);
}
function renderGrowth(d) {
  const n = d.n_days;
  const seg = `<span class="seg" role="group" aria-label="时间范围">${[7, 14, 30, 90].map((k) => `<button type="button" data-q="days=${k}" aria-pressed="${n === k}">近 ${k} 天</button>`).join('')}</span>`;
  const pd = perDay(d.total, 7);
  const posts = d.roi.reduce((a, r) => a + r.posts, 0);
  const fails = d.roi.reduce((a, r) => a + r.fails, 0);
  const expected = d.roi.reduce((a, r) => a + r.expected, 0);
  const span = d.fans_since && d.fans_since > d.days[0] ? `自 ${mdShort(d.fans_since)} 有记录起` : `近 ${n} 天`;
  const kpis = [
    ['粉丝总数', cnt('g_total', d.fans_total), '各账号去重后相加'],
    ['净增', isNum(d.fans_gain) ? `<span class="${cls(d.fans_gain)}">${sign(d.fans_gain)}</span>` : '—', span],
    ['日均净增（近 7 天）', isNum(pd) ? `<span class="${cls(pd)}">${pd >= 0 ? '+' : '−'}${fmtN(Math.abs(pd), 1)}</span>` : '—', isNum(pd) ? '' : '粉丝历史满 2 天后显示'],
    ['发出内容', cnt('g_posts', posts), expected ? `应发 ${expected}，完成 ${pct(posts / expected)}` : ''],
    ['每条带来粉丝', isNum(d.fans_gain) && posts ? fmtN(d.fans_gain / posts, 2) : '—', '净增 ÷ 发出条数'],
  ];
  const goal = d.goal ? `<section class="panel sec goal-p">${goalBlock(d.goal, d.fans_total, pd)}</section>` : '';
  const i0 = Math.max(0, d.total.findIndex(isNum)); // 有记录之前的日子不画，免得半张图是空的
  const tDays = d.days.slice(i0), tVals = d.total.slice(i0);
  const totalChart = tVals.filter(isNum).length >= 2
    ? chart(lineChart({ labels: tDays.map(mdShort), values: tVals, tips: tDays.map((day, i) => `${day}：${isNum(tVals[i]) ? fmtN(tVals[i], 0) + ' 粉丝' : '没有记录'}`) }), 240)
    : empty('粉丝历史不足 2 天，还画不出走势。粉丝采集每天跑一次，写入 state/fans_history.jsonl。');
  const gains = d.accounts.filter((a) => isNum(a.gain)).sort((a, b) => b.gain - a.gain);
  const gainChart = gains.length
    ? chart(barChart({ labels: gains.map((a) => a.name), values: gains.map((a) => a.gain), tips: gains.map((a) => `${a.name}（${a.platform}）：${sign(a.gain)}，现有 ${fmtN(a.fans, 0)}`), horizontal: true, color: css('--ok') }), Math.max(120, gains.length * 30 + 16))
    : empty('还没有可比较的粉丝变化。');
  const ins = growthInsights(d);
  const insBlock = ins.length ? `<ul class="insights">${ins.map(([k, t]) => `<li class="ins-${k}">${esc(t)}</li>`).join('')}</ul>` : '';
  const valsBy = Object.fromEntries(d.accounts.map((a) => [a.slot, a.values]));
  const def = { k: 'gain', dir: -1 };
  const rows = sortRows(d.roi, 'roi', def);
  const roiTbl = `<div class="tbl-wrap"><table class="t"><thead><tr>${th('roi', 'name', '账号', '', def)}${th('roi', 'fans', '粉丝', 'r', def)}${th('roi', 'gain', '净增', 'r', def)}
      <th>走势</th>${th('roi', 'gain_per_post', '每条涨粉', 'r', def)}${th('roi', 'posts', '发出', 'r', def)}${th('roi', 'expected', '应发（完成率）', 'r', def)}
      ${th('roi', 'fails', '失败', 'r', def)}${th('roi', 'views_per_post', '均播放', 'r', def)}${th('roi', 'inter_rate', '互动率', 'r', def)}${th('roi', 'gain_per_k_views', '每千播放涨粉', 'r', def)}${th('roi', 'follows', '作品涨粉', 'r', def)}</tr></thead>
    <tbody>${rows.map((r) => {
      const vals = valsBy[r.slot] || [];
      const pts = vals.map((v, i) => ({ day: d.days[i], n: v })).filter((p) => isNum(p.n));
      const done = r.expected ? r.posts / r.expected : null;
      return `<tr class="click" data-go="accounts/${esc(r.slot)}">
        <td>${who(r.pkey, r.name, r.platform)}${r.shared_with ? `<div class="sub">与「${esc(r.shared_with)}」同一个号</div>` : ''}</td>
        <td class="r">${fmtN(r.fans, 0)}</td><td class="r"><span class="delta ${cls(r.gain)}">${sign(r.gain)}</span></td>
        <td style="width:120px">${pts.length >= 2 ? chart(sparkChart(pts, r.pkey), 28) : '<span class="muted small">—</span>'}</td>
        <td class="r">${fmtN(r.gain_per_post, 2)}</td><td class="r">${r.posts}</td>
        <td class="r"><span class="${isNum(done) && done < 0.6 ? 'bad-t' : ''}">${r.expected}${isNum(done) ? `<span class="muted small">（${pct(done)}）</span>` : ''}</span></td>
        <td class="r">${r.fails ? `<span class="bad-t">${r.fails}</span>` : '<span class="muted">0</span>'}</td>
        <td class="r">${fmtN(r.views_per_post, 0)}</td><td class="r">${pct(r.inter_rate, 1)}</td><td class="r">${fmtN(r.gain_per_k_views, 1)}</td><td class="r">${fmtN(r.follows, 0)}</td></tr>`;
    }).join('')}</tbody></table></div>`;
  return `${errNote(d.errors)}<div class="toolbar">${seg}<span class="muted small">点表头排序，点行进账号详情</span></div>
    <div class="kpis k5" data-stagger>${kpis.map(([a, b, c]) => `<div class="panel kpi"><div class="k">${a}</div><div class="v">${b}</div>${c ? `<div class="s">${c}</div>` : ''}</div>`).join('')}</div>
    ${goal}
    <div class="sec grid cols-21">
      <section class="panel"><div class="panel-h"><h2>粉丝总数走势</h2><span class="meta">每天最后一次采集，缺的日子沿用前一天</span></div><div class="panel-b">${totalChart}</div></section>
      <section class="panel"><div class="panel-h"><h2>各账号净增</h2><span class="meta">${esc(span)}</span></div><div class="panel-b">${gainChart}</div></section>
    </div>
    ${insBlock ? `<section class="panel sec"><div class="panel-h"><h2>结论</h2><span class="meta">按上面的数据自动生成，样本少时只作提示</span></div><div class="panel-b">${insBlock}</div></section>` : ''}
    <section class="panel sec"><div class="panel-h"><h2>投入产出</h2><span class="meta">发出 = 按内容去重后成功发出的条数（重试不重复算）；作品涨粉只有部分平台提供</span>
      <span class="right"><button class="btn" type="button" data-csv="roi">${ico('download')}导出 CSV</button></span></div>
      <div class="panel-b flush">${roiTbl}</div></section>`;
}

/* ---------- 页面：日历 ---------- */
const WEEK = '一二三四五六日';
function hbCell(c, today) {
  const future = c.day > today;
  let k = 'none';
  if (c.expected || c.done || c.fail || c.queue) {
    if (c.fail && !c.done) k = 'fail';
    else if (future || (c.day === today && c.queue)) k = c.done >= c.expected && c.expected ? 'full' : 'pend';
    else if (c.expected && c.done >= c.expected) k = c.fail ? 'full warnish' : 'full';
    else if (c.done > 0) k = 'part';
    else if (c.expected) k = 'miss';
    else k = 'full';
  }
  const tip = `${c.day} 周${WD[new Date(c.day + 'T12:00:00Z').getUTCDay()]}\n应发 ${c.expected}，已发 ${c.done}${c.fail ? `，失败 ${c.fail}` : ''}${c.queue ? `，排队 ${c.queue}` : ''}`;
  return `<button type="button" class="hb ${k}${c.day === today ? ' today' : ''}" data-tip="${esc(tip)}" aria-label="${esc(tip)}" data-hb="${esc(c.day)}"></button>`;
}
function renderCalendar(d) {
  const cal = d.cal, g = d.growth;
  const start = cal.start;
  const today = cal.today;
  const thisMon = shiftDay(today, -((new Date(today + 'T12:00:00Z').getUTCDay() + 6) % 7));
  const end = cal.days[cal.days.length - 1];
  const nav = `<span class="daypick">
    <button class="btn" type="button" data-q="start=${esc(shiftDay(start, -7))}" aria-label="上一周">${ico('left')}</button>
    <button class="btn" type="button" data-q="start=${esc(thisMon)}" ${start === thisMon ? 'disabled' : ''}>本周</button>
    <button class="btn" type="button" data-q="start=${esc(shiftDay(start, 7))}" aria-label="下一周">${ico('right')}</button></span>
    <span class="wk-range num">${esc(start.slice(5).replace('-', '/'))} – ${esc(end.slice(5).replace('-', '/'))}</span>`;

  // 30 天心跳
  const hbRows = (cal.rows || []).map((a) => {
    const cells = (g.heartbeat[a.slot] || []);
    const exp = cells.reduce((s, c) => s + c.expected, 0), done = cells.reduce((s, c) => s + c.done, 0);
    return `<div class="hb-row"><div class="hb-lab">${logo(a.pkey)}<span class="nm">${esc(a.name)}</span><span class="c num">${done}/${exp}</span></div>
      <div class="hb-cells" style="--n:${cells.length}">${cells.map((c) => hbCell(c, today)).join('')}</div></div>`;
  }).join('');
  const hbAxis = `<div class="hb-row hb-ax"><div class="hb-lab"></div><div class="hb-cells" style="--n:${g.days.length}">${g.days.map((day, i) => `<span class="num">${i % 7 === (g.days.length - 1) % 7 ? +day.slice(8, 10) : ''}</span>`).join('')}</div></div>`;
  const hbLegend = `<div class="rd-legend"><span class="k"><span class="hb full"></span>发满</span><span class="k"><span class="hb part"></span>发了一部分</span>
    <span class="k"><span class="hb miss"></span>一条没发</span><span class="k"><span class="hb fail"></span>有失败没补上</span><span class="k"><span class="hb pend"></span>今天/排队中</span><span class="k"><span class="hb none"></span>不用发</span></div>`;
  const heart = `<section class="panel sec"><div class="panel-h"><h2>近 ${g.days.length} 天发布心跳</h2><span class="meta">每格一天，按内容计（同一条重试不重复算），点格子看那天的内容</span><span class="right">${hbLegend}</span></div>
    <div class="hb-wrap">${hbAxis}${hbRows}</div></section>`;

  // 周视图
  const head = cal.days.map((day, i) => {
    const t = cal.totals[i];
    const live = t.done + t.fail + t.queue + t.warn;
    return `<div class="wk-h${day === today ? ' today' : ''}"><div class="d">周${WEEK[i]} <span class="num">${+day.slice(5, 7)}/${+day.slice(8, 10)}</span></div>
      <div class="s num">${t.expected || live ? `${t.done}/${t.expected}` : '—'}${t.fail ? ` <span class="bad-t">✕${t.fail}</span>` : ''}</div></div>`;
  }).join('');
  const body = cal.rows.map((a) => `<div class="wk-lab">${logo(a.pkey)}<span class="nm">${esc(a.name)}</span></div>${a.cells.map((c, i) => {
    const day = cal.days[i];
    const its = c.items.filter((x) => !x.superseded_by);
    const ghosts = c.items.length - its.length;
    const missing = day < today ? Math.max(0, c.expected - c.done - c.queue) : 0;
    const show = its.slice(0, 4);
    return `<div class="wk-c${day === today ? ' today' : ''}${day > today ? ' future' : ''}">${show.map((x) => `
      <button type="button" class="wk-it b-${esc(x.bucket)}" data-item="${esc(x.id)}" data-tip="${esc(`${x.time} ${x.title || ''}\n${x.status_label}${x.reason ? `：${x.reason.label}` : ''}`)}">
        <span class="g" aria-hidden="true">${BUCKET[x.bucket]?.g || '·'}</span><span class="tm num">${esc(x.time || '')}</span><span class="tt">${esc(x.title || '（无标题）')}</span></button>`).join('')}
      ${its.length > show.length ? `<button type="button" class="wk-more" data-go="content?day=${esc(day)}&platform=${esc(a.pkey)}">还有 ${its.length - show.length} 条</button>` : ''}
      ${missing ? `<div class="wk-miss">缺 ${missing} 条</div>` : ''}${ghosts ? `<div class="wk-ghost" data-tip="失败后已重提的旧条目">已重提 ${ghosts}</div>` : ''}
      ${!c.items.length && !c.expected ? '<span class="wk-empty">·</span>' : ''}</div>`;
  }).join('')}`).join('');
  const week = `<section class="panel sec"><div class="panel-h"><h2>周排期</h2><span class="meta">每格是这个账号当天的内容，按时间排；格子底色越深说明越没发满</span></div>
    <div class="wk-wrap" data-keep-scroll="week"><div class="week" style="--n:${cal.days.length}"><div class="wk-corner"></div>${head}${body}</div></div></section>`;

  // 发布质量
  const pubRows = g.publish_daily.filter((r) => r.expected || r.done || r.fail || r.queue);
  const pub = pubRows.length >= 2 ? chart(pubChart({ days: pubRows.map((r) => r.day), rows: pubRows }), 220) : empty('至少两天的台账数据才画得出发布趋势。');
  const maxR = Math.max(1, ...g.reasons.map((r) => r.n));
  const reasons = g.reasons.length ? `<div class="reasons">${g.reasons.map((r) => `<div class="rs">
      <div class="rs-h"><b>${esc(r.label)}</b><span class="num">${r.n} 次</span></div>${bar(r.n / maxR, 'bad')}
      <div class="rs-hint">${esc(r.hint)}</div>
      <div class="rs-acc">${r.slots.slice(0, 4).map((s) => `<span class="src">${logo(s.pkey, 'sm')} ${esc(s.name)} ${s.n}</span>`).join('')}</div></div>`).join('')}</div>`
    : empty(`近 ${g.days.length} 天没有发布失败。`);
  const MODE_CN = { native: '平台定时', dispatch: '到点提交', web: '网页发表', draft: '草稿' };
  const modes = g.by_mode.length ? `<div class="tbl-wrap"><table class="t"><thead><tr><th>发布方式</th><th class="r">内容</th><th class="r">发出</th><th class="r">失败</th><th class="r">一次成功</th></tr></thead>
    <tbody>${g.by_mode.map((m) => `<tr><td>${esc(MODE_CN[m.mode] || m.mode)}</td><td class="r">${m.n}</td><td class="r">${m.done}</td><td class="r">${m.fail ? `<span class="bad-t">${m.fail}</span>` : 0}</td><td class="r">${pct(m.first_ok / m.n)}</td></tr>`).join('')}</tbody></table></div>` : '';
  const quality = `<div class="sec grid cols-21">
    <section class="panel"><div class="panel-h"><h2>每天发布结果</h2><span class="meta">按内容计；成功率 = 发出 ÷（发出 + 最终失败）</span></div><div class="panel-b">${pub}</div></section>
    <section class="panel"><div class="panel-h"><h2>发布方式</h2><span class="meta">一次成功 = 第一次提交就发出</span></div><div class="panel-b flush">${modes || empty('没有数据')}</div></section></div>
    <section class="panel sec"><div class="panel-h"><h2>失败原因</h2><span class="meta">近 ${g.days.length} 天每次失败的提交，按报错文字归类；同一条重试多次会算多次</span></div><div class="panel-b">${reasons}</div></section>`;

  return `${errNote({ ...cal.errors, ...g.errors })}<div class="toolbar">${nav}<span class="muted small kb-hint">快捷键 <kbd>[</kbd> <kbd>]</kbd> 切换周</span></div>${week}${heart}${quality}`;
}

/* ---------- 页面：账号 ---------- */
function renderAccounts(d) {
  const accs = d.accounts || [];
  if (!accs.length) return errNote(d.errors) + empty('config/schedule.json 里没有账号。');
  const cur = accs.find((a) => a.slot === S.route.arg) || accs[0];
  const list = accs.map((a) => `<button type="button" data-go="accounts/${esc(a.slot)}" aria-pressed="${a.slot === cur.slot}">
      ${logo(a.pkey)}<span class="nm">${esc(a.name)}</span><span class="v num">${fmtN(a.fans, 0)}</span></button>`).join('');
  const sp = cur.spark || [];
  const fansChart = sp.length >= 2
    ? chart(lineChart({ labels: sp.map((x) => mdShort(x.day)), values: sp.map((x) => x.n), tips: sp.map((x) => `${x.day}：${fmtN(x.n, 0)} 粉丝`), pk: cur.pkey }), 160)
    : empty(sp.length ? `粉丝历史只有 1 条（${esc(sp[0].day)}：${fmtN(sp[0].n, 0)}）。每天采集后这里画出走势。` : '还没有这个账号的粉丝记录。');
  const a = cur.avg || {};
  const hasRet = cur.posts.some((x) => isNum(x.bounce_2s));
  const kpis = [
    ['近 7 天作品', cnt('ak:n:' + cur.slot, cur.n), '创作者中心已采集'],
    ['播放/阅读合计', cnt('ak:v:' + cur.slot, cur.sum.views), ''],
    ['平均每条', fmtN(a.views, 1), '播放/阅读'],
    ['平均赞 + 藏', isNum(a.likes) || isNum(a.favorites) ? fmtN((a.likes || 0) + (a.favorites || 0), 2) : '—', ''],
    ['平均评论', fmtN(a.comments, 2), ''],
    ['涨粉合计', cnt('ak:f:' + cur.slot, cur.sum.follows), '作品带来的关注'],
  ];
  if (hasRet) kpis.push(['平均 2 秒跳出', pct(a.bounce_2s), '越低越好'], ['平均 5 秒完播', pct(a.completion_5s), '越高越好']);
  const postsTbl = cur.posts.length ? `<div class="tbl-wrap"><table class="t">
    <thead><tr><th>发布</th><th>标题</th><th class="r">播放</th><th class="r">赞</th><th class="r">藏</th><th class="r">评</th><th class="r">涨粉</th>
      ${hasRet ? '<th class="r">2秒跳出</th><th class="r">5秒完播</th>' : ''}<th>栏目</th><th>诊断</th></tr></thead>
    <tbody>${cur.posts.map((x) => `<tr class="${x.item_id ? 'click' : ''}" ${x.item_id ? `data-item="${esc(x.item_id)}"` : ''}>
      <td class="nowrap num">${esc(mdShort(x.created_iso))} ${esc(hm(x.created_iso))}</td><td class="tt"><div class="clamp2">${esc(x.title)}</div></td>
      <td class="r">${fmtN(x.views, 0)}</td><td class="r">${fmtN(x.likes, 0)}</td><td class="r">${fmtN(x.favorites, 0)}</td><td class="r">${fmtN(x.comments, 0)}</td><td class="r">${fmtN(x.follows, 0)}</td>
      ${hasRet ? `<td class="r">${pct(x.bounce_2s)}</td><td class="r">${pct(x.completion_5s)}</td>` : ''}
      <td>${x.column && x.column !== '未标' ? `<span class="tag">${esc(x.column)}</span>` : '<span class="muted small">未标</span>'}</td>
      <td>${x.tips.length ? `<span class="diag-n" data-tip="${esc(x.tips.join('\n'))}">${x.tips.length}</span>` : '<span class="muted">—</span>'}</td></tr>`).join('')}</tbody></table></div>`
    : empty('近 7 天没有采集到这个账号的作品数据。数据回流在 12:40、22:40 采集创作者中心。');
  const led = cur.ledger || [];
  const ledList = led.length ? `<ul class="list" data-stagger>${led.map((i) => `<li class="li" style="grid-template-columns:96px minmax(0,1fr) auto;align-items:center">
      <span class="num small muted">${esc(mdShort(i.day))} ${esc(i.time)}</span>
      <span><a href="javascript:void 0" data-item="${esc(i.id)}">${esc(i.title || '（无标题）')}</a>${i.column ? ` <span class="tag">${esc(i.column)}</span>` : ''}${i.superseded_by ? ' <span class="muted small">已重提</span>' : ''}</span>
      <span>${pill(i.superseded_by ? 'muted' : i.bucket, i.status_label)}</span></li>`).join('')}</ul>`
    : empty('近 7 天台账里没有这个账号的条目。');
  return `${errNote(d.errors)}<div class="acc-layout">
    <nav class="panel acc-list" aria-label="账号列表">${list}</nav>
    <div class="grid" style="gap:16px">
      <section class="panel acc-head">
        <div>
          <div class="who">${logo(cur.pkey, 'lg')}<span><span class="nm" style="font-size:16px">${esc(cur.name)}</span><br><span class="pf">${esc(cur.platform)}，每日 ${esc((cur.times || []).join('、') || '—')}${cur.weekdays_only ? '（仅工作日）' : ''}${cur.paused ? '，已暂停' : ''}</span></span></div>
          <div class="big">${cnt('acc_fans:' + cur.slot, cur.fans)}</div>
          <div class="ds">${delta(cur.d1, '较昨日')}${cur.d7_span > 1 ? delta(cur.d7, `较 ${cur.d7_span} 天前`) : '<span class="delta none">较 7 天前 —</span>'}<span>今日应发 ${cur.expected_today}</span></div>
        </div>
        <div><div class="muted small" style="margin-bottom:4px">粉丝走势</div>${fansChart}</div>
      </section>
      <div class="kpis ${kpis.length === 8 ? 'k4' : 'k3'}" data-stagger>${kpis.map(([k, v, s]) => `<div class="panel kpi"><div class="k">${k}</div><div class="v">${v}</div>${s ? `<div class="s">${s}</div>` : ''}</div>`).join('')}</div>
      <section class="panel"><div class="panel-h"><h2>近 7 天作品数据</h2><span class="meta">创作者中心最新快照，诊断来自 metrics.py</span></div><div class="panel-b flush">${postsTbl}</div></section>
      <section class="panel"><div class="panel-h"><h2>近 7 天台账</h2><span class="meta">${led.length} 条</span></div>${ledList}</section>
    </div></div>`;
}

/* ---------- 页面：内容 ---------- */
function daypick(day, days) {
  const opts = (days || []).includes(day) ? days : [day, ...(days || [])];
  return `<span class="daypick">
    <button class="btn" type="button" data-day="${esc(shiftDay(day, -1))}" aria-label="前一天">‹</button>
    <select class="select" data-dayselect aria-label="选择日期">${opts.map((x) => `<option value="${esc(x)}" ${x === day ? 'selected' : ''}>${esc(dayLabel(x))}</option>`).join('')}</select>
    <button class="btn" type="button" data-day="${esc(shiftDay(day, 1))}" aria-label="后一天" ${day >= todayStr() ? 'disabled' : ''}>›</button></span>`;
}
function renderContent(d) {
  const q = S.route.q;
  const all = d.items;
  let items = all;
  if (q.platform) items = items.filter((i) => i.pkey === q.platform);
  if (q.status) items = items.filter((i) => i.bucket === q.status);
  if (q.column) items = items.filter((i) => (i.column || '未标') === q.column);
  const plats = PLAT_ORDER.filter((k) => d.platforms.includes(k));
  const pf = `<span class="plat-filter" role="group" aria-label="平台">
    <button type="button" class="all" data-q="platform=" aria-pressed="${!q.platform}">全部</button>
    ${plats.map((k) => `<button type="button" data-q="platform=${k}" aria-pressed="${q.platform === k}">${logo(k)}${esc(PLAT[k].name)}</button>`).join('')}</span>`;
  const st = [['', '全部'], ['done', '已发'], ['queue', '排队'], ['fail', '失败'], ['warn', '待核实'], ['muted', '其他']];
  const seg = `<span class="seg" role="group" aria-label="状态">${st.map(([k, n]) => `<button type="button" data-q="status=${k}" aria-pressed="${(q.status || '') === k}">${n}</button>`).join('')}</span>`;
  const cols = [...new Set([...(d.columns || []), ...(all.some((i) => !i.column) ? ['未标'] : [])])];
  const colSel = `<select class="select" data-qselect="column" aria-label="栏目"><option value="">全部栏目</option>${cols.map((c) => `<option value="${esc(c)}" ${q.column === c ? 'selected' : ''}>${esc(c)}</option>`).join('')}</select>`;
  const c = d.counts || {};
  const supersededN = all.filter((i) => i.superseded_by).length;
  const counts = `<div class="counts"><span>当天共 <b>${cnt('c_all', all.length)}</b> 条</span><span>已发 <b>${cnt('c_done', c.done || 0)}</b></span><span>排队 <b>${cnt('c_queue', c.queue || 0)}</b></span>
    <span>失败 <b>${cnt('c_fail', c.fail || 0)}</b>${supersededN ? `（其中 ${supersededN} 条已重提）` : ''}</span>${c.warn ? `<span>待核实 <b>${c.warn}</b></span>` : ''}<span>其他 <b>${c.muted || 0}</b></span>
    ${items.length !== all.length ? `<span>筛选后 <b>${items.length}</b> 条</span>` : ''}</div>`;
  const view = store.get('content.view', 'grid');
  const ft = (i) => esc(`${i.title || ''} ${i.account_name || ''} ${i.column || ''} ${i.id || ''}`.toLowerCase());
  const listTbl = () => `<section class="panel"><div class="tbl-wrap"><table class="t"><thead><tr><th>时间</th><th>账号</th><th>标题</th><th>栏目</th><th>状态</th><th>链接</th></tr></thead>
    <tbody>${items.map((i) => `<tr class="click${i.bucket === 'muted' || i.superseded_by ? ' dimrow' : ''}" data-item="${esc(i.id)}" data-ft="${ft(i)}">
      <td class="num nowrap">${esc(i.time || '--:--')}</td><td>${who(i.pkey, i.account_name || PLAT[i.pkey]?.name || '')}</td>
      <td class="tt"><div class="clamp2">${esc(i.title || '（无标题）')}</div>${i.reason ? `<div class="sub">${esc(i.reason.label)}：${esc((i.detail_text || '').slice(0, 60))}</div>` : ''}</td>
      <td>${i.column ? `<span class="tag">${esc(i.column)}</span>` : '<span class="muted small">—</span>'}</td>
      <td>${i.superseded_by ? pill('muted', '已重提') : pill(i.bucket, i.status_label)}</td>
      <td>${i.url ? `<a href="${esc(i.url)}" target="_blank" rel="noopener noreferrer" data-stop>打开</a>` : '<span class="muted small">—</span>'}</td></tr>`).join('')}</tbody></table></div></section>`;
  const body = !items.length
    ? empty(all.length ? '没有符合筛选条件的内容。换个平台或状态试试。' : `${esc(dayLabel(d.day))}的台账里还没有内容。选题和制作完成后，入账的条目会出现在这里。`)
    : view === 'list' ? listTbl() : `<div class="cgrid" data-stagger>${items.map((i) => card(i, ft(i))).join('')}</div>`;
  const tools = `<span class="tool-r"><input class="input" type="search" data-filter="content" placeholder="在当天筛选标题、账号" value="${esc(S.ui.filter.content || '')}" aria-label="筛选">
    <span class="seg" role="group" aria-label="显示方式"><button type="button" data-view="grid" aria-pressed="${view !== 'list'}" title="卡片">${ico('grid')}</button><button type="button" data-view="list" aria-pressed="${view === 'list'}" title="列表">${ico('list')}</button></span></span>`;
  return `${errNote(d.errors)}<div class="toolbar">${daypick(d.day, d.days)}${pf}</div>
    <div class="toolbar">${seg}${colSel}${tools}</div>${counts}<div class="filter-empty" hidden>${empty('当天没有标题或账号包含这个词的内容。全局搜索用 ⌘K。')}</div>${body}`;
}
/* 当天内的文字筛选：直接隐藏不匹配的卡片/行，不重画，输入框不丢焦点 */
function applyFilter(q) {
  const k = (q || '').trim().toLowerCase();
  let shown = 0, total = 0;
  $$('#page [data-ft]').forEach((el) => { total++; const hit = !k || el.dataset.ft.includes(k); el.hidden = !hit; if (hit) shown++; });
  const fe = $('#page .filter-empty');
  if (fe) fe.hidden = !(total && !shown);
}
function card(i, ft = '') {
  const dim = i.bucket === 'muted' || i.superseded_by;
  const st = i.superseded_by ? pill('muted', '已重提') : pill(i.bucket, i.status_label);
  const thumb = i.thumb
    ? `<img loading="lazy" src="${esc(i.thumb)}" alt="" onload="this.classList.add('ok');this.naturalWidth>this.naturalHeight*1.15&&this.classList.add('wide')" onerror="this.remove()">`
    : `<div class="ph">${logo(i.pkey, 'xl')}<span>${esc(i.is_answer ? '知乎回答' : PTYPE[i.publish_type] || '无封面')}</span></div>`;
  return `<button type="button" class="card lift${dim ? ' dim' : ''}" data-item="${esc(i.id)}"${ft ? ` data-ft="${ft}"` : ''}>
    <div class="thumb"${i.thumb ? ` style="--img:url('${esc(i.thumb)}')"` : ''}>${thumb}<span class="time num">${esc(i.time || '--:--')}</span>${i.publish_type === 'video' ? '<span class="vid">视频</span>' : ''}</div>
    <div class="card-b">
      <div>${who(i.pkey, i.account_name || PLAT[i.pkey]?.name || '')}</div>
      <div class="title clamp2">${esc(i.title || '（无标题）')}</div>
      <div class="row">${st}${i.column ? `<span class="tag">${esc(i.column)}</span>` : ''}</div>
    </div></button>`;
}

/* ---------- 抽屉：内容详情 ---------- */
/* 抽屉里的上一条/下一条：按当前页面上内容出现的顺序 */
function collectItems() {
  const seen = new Set();
  return $$('#page [data-item]').filter((el) => !el.closest('[hidden]') && !el.hidden).map((el) => el.dataset.item).filter((id) => !seen.has(id) && seen.add(id));
}
function drawerNav() {
  const list = S.drawerList || [];
  const i = list.indexOf(S.drawerId);
  return `<span class="dnav"><button class="btn icon" type="button" data-dstep="-1" ${i <= 0 ? 'disabled' : ''} aria-label="上一条（←）" title="上一条（←）">${ico('left')}</button>
    <span class="muted small num">${i >= 0 ? `${i + 1}/${list.length}` : ''}</span>
    <button class="btn icon" type="button" data-dstep="1" ${i < 0 || i >= list.length - 1 ? 'disabled' : ''} aria-label="下一条（→）" title="下一条（→）">${ico('right')}</button></span>`;
}
function stepDrawer(k) {
  const list = S.drawerList || [];
  const i = list.indexOf(S.drawerId);
  const nx = list[i + k];
  if (i >= 0 && nx) openDrawer(nx, { keepList: true });
}
async function openDrawer(id, { keepList = false } = {}) {
  const wasOpen = !!S.drawerId;
  S.drawerId = id;
  if (!keepList) S.drawerList = collectItems();
  if (!wasOpen) S.drawerReturn = document.activeElement;
  syncItemParam(id);
  const dr = $('#drawer');
  $('#drawerHead').innerHTML = `<div class="grow"><div class="sk sk-line" style="width:40%"></div></div>${drawerNav()}<button class="btn ghost" type="button" data-close aria-label="关闭（Esc）">关闭</button>`;
  $('#drawerBody').innerHTML = `<div class="sk-wrap"><div class="sk" style="height:26px;width:75%"></div><div class="sk" style="height:110px"></div><div class="sk" style="height:240px"></div></div>`;
  dr.classList.add('open');
  dr.setAttribute('aria-hidden', 'false');
  $('#scrim').classList.add('open');
  if (!wasOpen) $('#drawerHead [data-close]').focus();
  try {
    const d = await api('/api/content/' + encodeURIComponent(id));
    if (S.drawerId !== id) return;
    renderDrawer(d);
  } catch (e) {
    if (S.drawerId !== id) return;
    $('#drawerBody').innerHTML = empty(`读取失败：${esc(e.message)}。这条内容可能已从台账删除。`);
  }
}
function closeDrawer() {
  S.drawerId = null;
  S.drawerData = null;
  $('#drawer').classList.remove('open');
  $('#drawer').setAttribute('aria-hidden', 'true');
  $('#scrim').classList.remove('open');
  $$('#drawer video').forEach((v) => v.pause());
  disposeCharts($('#drawer'));
  closeSheet();
  syncItemParam(null);
  if (S.drawerReturn && S.drawerReturn.focus && S.drawerReturn.isConnected) S.drawerReturn.focus();
}
function renderDrawer(d) {
  const i = d.item;
  S.drawerData = d;
  rememberRecent(i);
  const st = i.superseded_by ? pill('muted', '已由重提替代') : pill(i.bucket, i.status_label);
  $('#drawerHead').innerHTML = `${logo(i.pkey, 'lg')}<div class="grow"><div class="nm1">${esc(i.account_name || PLAT[i.pkey]?.name || '')}</div>
    <div class="muted small">${esc(PLAT[i.pkey]?.name || i.platform_name || '')}，${esc(dayLabel(i.day))} ${esc(i.time)}</div></div>${st}${drawerNav()}
    <button class="btn ghost" type="button" data-close aria-label="关闭（Esc）">关闭</button>`;
  const p = d.post || {};
  const kv = [
    ['形式', PTYPE[i.publish_type] || i.kind || i.publish_type],
    ['栏目', i.column || p.column],
    ['发布方式', MODE[i.mode] || i.mode],
    ['短标题', p.short_title],
    ['话题', Array.isArray(p.tags) ? p.tags.join('、') : p.tags],
    ['链接', i.url ? ext(i.url, i.url.length > 80 ? i.url.slice(0, 80) + '…' : i.url) : ''],
    ['台账 ID', i.is_answer ? '' : i.id],
    ['更新于', i.updated ? `${mdShort(i.updated)} ${hm(i.updated)}` : ''],
  ].filter(([, v]) => v);
  const parts = [];
  const actions = `<div class="dacts">
    <button class="btn" type="button" data-copy="title">${ico('copy')}复制标题</button>
    ${d.description ? `<button class="btn" type="button" data-copy="desc">${ico('copy')}复制文案</button>` : ''}
    ${i.url ? `<button class="btn" type="button" data-copy="url">${ico('link')}复制链接</button><a class="btn" href="${esc(i.url)}" target="_blank" rel="noopener noreferrer">${ico('ext')}打开原帖</a>` : ''}
    <button class="btn ghost" type="button" data-copy="share" title="复制工作台里这条内容的地址">${ico('link')}复制本页地址</button></div>`;
  parts.push(`<div><h2 class="title">${esc(i.title || '（无标题）')}</h2>${actions}<dl class="kv">${kv.map(([k, v]) => `<dt>${k}</dt><dd>${k === '链接' ? v : esc(v)}</dd>`).join('')}</dl></div>`);
  if (i.detail_text || i.superseded_by) {
    parts.push(`<div class="dsec"><h3>状态说明</h3>${i.superseded_by ? `<div class="note-box" style="margin-bottom:8px">这条已由 ${esc(i.superseded_by)} 重新提交，不再计入失败。</div>` : ''}
      ${i.detail_text ? `<div class="note-box ${i.bucket === 'fail' && !i.superseded_by ? 'bad' : ''}">${esc(i.detail_text)}</div>` : ''}
      ${i.reason && !i.superseded_by ? `<div class="fix" style="margin-top:8px">${ico('bolt')}<span><b>${esc(i.reason.label)}</b>：${esc(i.reason.hint)}</span></div>` : ''}</div>`);
  }
  const md = d.media || {};
  if ((md.videos || []).length) {
    const vids = md.videos.slice(0, 2);
    parts.push(`<div class="dsec"><h3>视频<span class="meta">${md.videos.length} 个文件</span></h3><div class="videos ${vids.length > 1 ? 'two' : ''}">
      ${vids.map((v) => `<div><video controls preload="metadata" playsinline src="${esc(v.url)}" ${(md.final || [])[0] ? `poster="${esc(md.final[0].url)}"` : ''}></video><div class="muted small" style="margin-top:4px">${esc(v.name)}</div></div>`).join('')}</div></div>`);
  }
  if ((md.final || []).length) parts.push(`<div class="dsec"><h3>成品图片<span class="meta">${md.final.length} 张，点开看原图</span></h3>${gallery(md.final)}</div>`);
  parts.push(`<div class="dsec"><h3>作品数据</h3>${metricsBlock(d.metrics)}</div>`);
  if (d.body_html) parts.push(`<div class="dsec"><h3>正文</h3><div class="md">${d.body_html}</div></div>`);
  else if (d.description) parts.push(`<div class="dsec"><h3>文案</h3><div class="note-box">${esc(d.description)}</div></div>`);
  if (d.review_html) parts.push(`<div class="dsec"><h3>审稿记录<span class="meta">review.md</span></h3><div class="md">${d.review_html}</div></div>`);
  if ((d.events || []).length) {
    parts.push(`<div class="dsec"><h3>流程记录</h3>${d.events.map((e) => `<div class="ev"><span class="num muted">${esc(mdShort(e.at))} ${esc(hm(e.at))}</span><span>${esc(EVK[e.kind] || e.kind)}</span><span class="muted">${esc(e.text)}</span></div>`).join('')}</div>`);
  }
  const variants = (md.process || []).filter((m) => m.variant);
  const proc = (md.process || []).filter((m) => !m.variant);
  if (variants.length) parts.push(`<div class="dsec"><h3>封面其他尺寸<span class="meta">${variants.length} 张</span></h3>${gallery(variants, true)}</div>`);
  if (proc.length) parts.push(`<details class="fold"><summary>过程文件 ${proc.length} 个（检查图、关键帧、原图）</summary><div>${gallery(proc)}</div></details>`);
  if (d.detail_raw) parts.push(`<details class="fold"><summary>发布返回原文</summary><div><pre class="raw">${esc(d.detail_raw)}</pre></div></details>`);
  if (Object.keys(d.errors || {}).length) parts.push(errNote(d.errors));
  disposeCharts($('#drawer'));
  const body = $('#drawerBody');
  body.innerHTML = parts.join('');
  body.scrollTop = 0;
  $$('.md a', body).forEach((a) => { a.target = '_blank'; a.rel = 'noopener noreferrer'; });
  mountCharts(body, true);
  Motion.drawer(body);
}
function gallery(list, fit) {
  return `<div class="gallery${fit ? ' fit' : ''}">${list.map((m) => `<div><a href="${esc(m.url)}" target="_blank" rel="noopener"><img loading="lazy" src="${esc(m.url)}" alt="${esc(m.name)}"></a><div class="cap">${esc(m.name)}</div></div>`).join('')}</div>`;
}
function metricsBlock(m) {
  if (!m) return empty('还没有这条作品的创作者中心数据。采集后按作品链接或标题自动匹配。');
  const L = m.latest || {};
  const keys = Object.keys(MLABEL).filter((k) => k in L && k !== 'type');
  const snap = L.snap ? new Date(L.snap * 1000) : null;
  let h = `<div class="kpis">${keys.map((k) => `<div class="panel kpi" style="padding:10px 12px"><div class="k">${MLABEL[k]}</div><div class="v" style="font-size:20px">${PCT_KEYS.has(k) ? pct(L[k]) : fmtN(L[k], 1)}</div></div>`).join('')}</div>`;
  h += `<div class="muted small" style="margin-top:6px">最新快照 ${snap ? esc(`${snap.getMonth() + 1}-${String(snap.getDate()).padStart(2, '0')} ${String(snap.getHours()).padStart(2, '0')}:${String(snap.getMinutes()).padStart(2, '0')}`) : ''}，共 ${(m.series || []).length} 次采集</div>`;
  if ((m.series || []).length >= 2) {
    h += `<div style="margin-top:10px">${chart(lineChart({ labels: m.series.map((s) => s.at.slice(5, 16).replace('T', ' ')), values: m.series.map((s) => s.m.views || 0), tips: m.series.map((s) => `${s.at.slice(5, 16).replace('T', ' ')}：播放 ${fmtN(s.m.views, 0)}`) }), 150)}</div>`;
  }
  if ((m.tips || []).length) h += `<ul class="tips">${m.tips.map((t) => `<li>${esc(t)}</li>`).join('')}</ul>`;
  return h;
}

/* ---------- 页面：数据 ---------- */
function renderData(d) {
  const days = d.days;
  const k = d.kpi || {};
  const seg = `<span class="seg" role="group" aria-label="时间范围">${[7, 14, 30, 90].map((n) => `<button type="button" data-q="days=${n}" aria-pressed="${days === n}">近 ${n} 天</button>`).join('')}</span>`;
  if (!d.rows.length) {
    return `${errNote(d.errors)}<div class="toolbar">${seg}</div>` + empty(`近 ${days} 天还没有作品数据。数据回流在每天 12:40 和 22:40 采集各平台创作者中心，入库后这里自动出现。`);
  }
  const kp = d.kpi_prev;
  const vs = (key) => {
    if (!kp || !isNum(kp[key]) || !isNum(k[key])) return '';
    if (!kp[key]) return k[key] ? '<span class="delta up">上一期为 0</span>' : '';
    const r = (k[key] - kp[key]) / kp[key];
    return `<span class="delta ${r > 0.005 ? 'up' : r < -0.005 ? 'down' : 'flat'}" data-tip="${esc(`上一期（再往前 ${days} 天）：${fmtN(kp[key], 0)}`)}">${r >= 0 ? '+' : '−'}${pct(Math.abs(r))} 较上一期</span>`;
  };
  const kpis = [
    ['作品数', cnt('dk_posts', k.posts), `近 ${days} 天发布并已采集 ${vs('posts')}`],
    ['播放/阅读合计', cnt('dk_views', k.views), `${k.posts ? `平均每条 ${fmtN(k.views / k.posts, 1)}` : ''} ${vs('views')}`],
    ['互动合计', cnt('dk_inter', k.inter), `赞、藏、评、转 ${vs('inter')}`],
    ['作品涨粉', cnt('dk_follows', k.follows), `只有部分平台提供 ${vs('follows')}`],
  ];
  const mult = d.series.map((s) => {
    const tot = s.points.reduce((a, p) => a + p.views, 0);
    return `<div class="panel mult"><div class="mult-h">${logo(s.pkey)}${esc(s.platform_name)}<span class="meta num">合计 ${fmtN(tot, 0)}</span></div>
      ${chart(barChart({ labels: s.points.map((p) => +p.day.slice(8, 10) + '日'), values: s.points.map((p) => p.views), tips: s.points.map((p) => `${p.day}：${p.n} 条作品，播放/阅读 ${fmtN(p.views, 0)}`), pk: s.pkey }), 130)}</div>`;
  }).join('');
  const colNote = d.by_column.length === 1 && d.by_column[0].key === '未标' ? '<div class="muted small" style="margin-top:6px">这些作品发布时还没写栏目（post.json 的 column），所以都归在「未标」。</div>' : '';
  const colChart = chart(barChart({ labels: d.by_column.map((c) => c.key), values: d.by_column.map((c) => c.views_avg), tips: d.by_column.map((c) => `${c.key}：${c.n} 条，平均播放 ${fmtN(c.views_avg, 1)}，均赞藏 ${fmtN(c.inter_avg, 2)}`), horizontal: true }), Math.max(70, d.by_column.length * 34 + 16));
  const hours = Array.from({ length: 24 }, (_, h) => d.by_hour.find((x) => x.key === String(h).padStart(2, '0') + '点'));
  const hourChart = chart(barChart({ labels: hours.map((_, h) => String(h)), values: hours.map((a) => (a ? a.views_avg : 0)), tips: hours.map((a, h) => (a ? `${h} 点发布：${a.n} 条，平均播放 ${fmtN(a.views_avg, 1)}` : `${h} 点：没有作品`)) }), 170);
  const ret = d.rows.filter((x) => isNum(x.bounce_2s) || isNum(x.completion_5s));
  const cellBar = (v, th, badHigh) => {
    if (!isNum(v)) return '<span class="muted">—</span>';
    const bad = badHigh ? v >= th : v < th;
    return `<span class="cell-bar" data-tip="${esc(`${pct(v)}，参考线 ${pct(th)}（${badHigh ? '高于' : '低于'}参考线说明开头要改）`)}"><span class="bar"><i class="${bad ? 'bad' : ''}" style="width:${Math.min(100, v * 100)}%"></i><b style="left:${th * 100}%"></b></span><span class="v num ${bad ? 'bad' : ''}">${pct(v)}</span></span>`;
  };
  const retTbl = ret.length ? `<div class="tbl-wrap"><table class="t"><thead><tr><th>发布</th><th>标题</th><th class="r">时长</th><th class="r">播放</th><th>2 秒跳出（参考线 35%）</th><th>5 秒完播（参考线 50%）</th><th class="r">平均观看占比</th></tr></thead>
    <tbody>${ret.map((x) => `<tr class="${x.item_id ? 'click' : ''}" ${x.item_id ? `data-item="${esc(x.item_id)}"` : ''}><td class="nowrap num">${esc(mdShort(x.created_iso))} ${esc(hm(x.created_iso))}</td><td class="tt"><div class="clamp2">${esc(x.title)}</div></td>
      <td class="r">${x.duration ? x.duration + '秒' : '—'}</td><td class="r">${fmtN(x.views, 0)}</td><td>${cellBar(x.bounce_2s, 0.35, true)}</td><td>${cellBar(x.completion_5s, 0.5, false)}</td><td class="r">${pct(x.avg_view_ratio)}</td></tr>`).join('')}</tbody></table></div>`
    : empty('这段时间没有带留存数据的视频（目前只有抖音创作者中心提供 2 秒跳出和 5 秒完播）。');
  const gtab = S.ui.tab.group || 'platform';
  const groups = { platform: ['平台', d.by_platform], column: ['栏目', d.by_column], hour: ['发布时段', d.by_hour], len: ['时长/形式', d.by_len] };
  const g = groups[gtab][1];
  const aggTbl = `<div class="subtabs" role="tablist" style="margin:0 18px 0">${Object.entries(groups).map(([kk, [n]]) => `<button type="button" role="tab" data-tab="group:${kk}" aria-selected="${gtab === kk}">按${n}</button>`).join('')}</div>
    <div class="tbl-wrap"><table class="t"><thead><tr><th>${groups[gtab][0]}</th><th class="r">条数</th><th class="r">播放合计</th><th class="r">均播放</th><th class="r">均赞藏</th><th class="r">评论</th><th class="r">涨粉</th><th class="r">均 2 秒跳出</th><th class="r">均 5 秒完播</th></tr></thead>
    <tbody>${g.map((a) => `<tr><td>${esc(a.key)}</td><td class="r">${a.n}</td><td class="r">${fmtN(a.views, 0)}</td><td class="r">${fmtN(a.views_avg, 1)}</td><td class="r">${fmtN(a.inter_avg, 2)}</td><td class="r">${fmtN(a.comments, 0)}</td><td class="r">${fmtN(a.follows, 0)}</td><td class="r">${pct(a.b2_avg)}</td><td class="r">${pct(a.c5_avg)}</td></tr>`).join('')}</tbody></table></div>`;
  return `${errNote(d.errors)}<div class="toolbar">${seg}<span class="muted small">创作者中心最新采集 ${esc(mdShort(k.snap_latest))} ${esc(hm(k.snap_latest))}，每条作品取最新快照</span></div>
    <div class="kpis k4" data-stagger>${kpis.map(([a, b, c]) => `<div class="panel kpi"><div class="k">${a}</div><div class="v">${b}</div><div class="s">${c}</div></div>`).join('')}</div>
    <div class="sec"><div class="sec-h"><h2>每日播放/阅读</h2><span class="meta">按作品发布日汇总，各平台纵轴独立</span></div><div class="multiples" data-stagger style="--n:${balancedCols(d.series.length)}">${mult}</div></div>
    <div class="sec grid cols-2">
      <section class="panel"><div class="panel-h"><h2>栏目对比</h2><span class="meta">平均每条播放/阅读</span></div><div class="panel-b">${colChart}${colNote}</div></section>
      <section class="panel"><div class="panel-h"><h2>发布时段</h2><span class="meta">按发布小时，平均每条播放/阅读</span></div><div class="panel-b">${hourChart}</div></section>
    </div>
    <section class="panel sec"><div class="panel-h"><h2>视频开头留存</h2><span class="meta">2 秒跳出越低越好，5 秒完播越高越好；橙色表示越过参考线</span></div><div class="panel-b flush">${retTbl}</div></section>
    <section class="panel sec"><div class="panel-h"><h2>汇总</h2></div>${aggTbl}</section>
    <section class="panel sec"><div class="panel-h"><h2>作品明细</h2><span class="meta">${d.rows.length} 条，点表头排序，点行看诊断${d.diagnosis_available ? '' : '（诊断模块未加载）'}</span>
      <span class="right"><input class="input" type="search" data-filter="posts" placeholder="筛选标题" value="${esc(S.ui.filter.posts || '')}" aria-label="筛选作品"><button class="btn" type="button" data-csv="posts">${ico('download')}导出 CSV</button></span></div>
      <div class="filter-empty" hidden>${empty('没有标题包含这个词的作品。')}</div><div class="panel-b flush">${postsTable(d.rows)}</div></section>`;
}
function postsTable(rows) {
  const s = S.ui.sort.posts || { k: 'created', dir: -1 };
  const cols = [
    ['platform_name', '平台', ''], ['created', '发布', ''], ['title', '标题', ''], ['views', '播放', 'r'], ['likes', '赞', 'r'], ['favorites', '藏', 'r'],
    ['comments', '评', 'r'], ['shares', '转', 'r'], ['follows', '涨粉', 'r'], ['bounce_2s', '2秒跳出', 'r'], ['completion_5s', '5秒完播', 'r'], ['avg_view_ratio', '均看占比', 'r'], ['tips', '诊断', 'r'],
  ];
  const val = (x, k) => (k === 'tips' ? x.tips.length : x[k]);
  const sorted = [...rows].sort((a, b) => {
    const va = val(a, s.k), vb = val(b, s.k);
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    return (va > vb ? 1 : va < vb ? -1 : 0) * s.dir;
  });
  const openTips = S.ui.openTips;
  return `<div class="tbl-wrap"><table class="t"><thead><tr>${cols.map(([k, n, c]) => `<th class="sort ${c}" data-sort="${k}" ${s.k === k ? `aria-sort="${s.dir > 0 ? 'ascending' : 'descending'}"` : ''} tabindex="0">${n}</th>`).join('')}</tr></thead>
  <tbody>${sorted.map((x) => {
    const key = x.platform + ':' + x.id;
    const row = `<tr class="click" data-toggle="${esc(key)}" data-ft="${esc(`${x.title || ''} ${x.account_name || ''} ${x.column || ''}`.toLowerCase())}"><td>${logo(x.pkey)}</td><td class="nowrap num">${esc(mdShort(x.created_iso))} ${esc(hm(x.created_iso))}</td>
      <td class="tt"><div class="clamp2">${esc(x.title)}</div>${x.column && x.column !== '未标' ? `<span class="sub">${esc(x.column)}</span>` : ''}</td>
      <td class="r">${fmtN(x.views, 0)}</td><td class="r">${fmtN(x.likes, 0)}</td><td class="r">${fmtN(x.favorites, 0)}</td><td class="r">${fmtN(x.comments, 0)}</td><td class="r">${fmtN(x.shares, 0)}</td>
      <td class="r">${fmtN(x.follows, 0)}</td><td class="r">${pct(x.bounce_2s)}</td><td class="r">${pct(x.completion_5s)}</td><td class="r">${pct(x.avg_view_ratio)}</td>
      <td class="r">${x.tips.length ? `<span class="diag-n">${x.tips.length}</span>` : '<span class="muted">—</span>'}</td></tr>`;
    const tips = openTips[key] ? `<tr class="tips-row"><td></td><td colspan="12">${x.tips.length ? `<ul class="tips" style="margin:0">${x.tips.map((t) => `<li>${esc(t)}</li>`).join('')}</ul>` : '<span class="muted small">这条没有诊断提示。</span>'}
      ${x.item_id ? `<div style="margin-top:8px"><button class="btn" type="button" data-item="${esc(x.item_id)}">打开内容详情</button></div>` : '<div class="muted small" style="margin-top:6px">台账里没有对应条目（早期作品、网页直发或标题改过）。</div>'}</td></tr>` : '';
    return row + tips;
  }).join('')}</tbody></table></div>`;
}

/* ---------- 页面：互动 ---------- */
function renderEngagement(d) {
  const ba = d.by_action || {};
  const dayWord = d.day === todayStr() ? '今日' : '当天';
  const kpis = [[dayWord + '互动', d.total], ['评论', ba.comment || 0], ['回复', ba.reply || 0], ['点赞', ba.like || 0], ['关注', ba.follow || 0], ['浏览', ba.browse || 0]];
  const plats = d.platforms.map((p) => {
    const shown = p.actions.filter((a) => a.cap > 0 || (a.cap == null && a.used > 0) || (a.cap === 0 && a.used > 0));
    const body = p.disabled && !p.total
      ? '<div class="muted small">这个平台只回复自己作品下的留言，不做主动评论、点赞和关注。</div>'
      : shown.map((a) => a.cap > 0
        ? `<div class="meter"><span class="ink2">${esc(a.label)}</span>${bar(a.used / a.cap, a.used >= a.cap ? 'max' : a.used / a.cap >= 0.8 ? 'hi' : '', `${a.label} 已用 ${a.used}，上限 ${a.cap}`)}<span class="v num"><b>${a.used}</b>/${a.cap}</span></div>`
        : `<div class="meter"><span class="ink2">${esc(a.label)}</span><span class="muted small">不设上限</span><span class="v num"><b>${a.used}</b> 次</span></div>`).join('');
    return `<section class="panel eng-p"><div class="h">${logo(p.pkey)}<b>${esc(p.platform_name)}</b><span class="tot">${dayWord} ${cnt('et:' + p.pkey, p.total)} 次</span></div>${body}</section>`;
  }).join('');
  const feed = d.recent.length ? `<ul class="list" data-stagger>${d.recent.map((r) => `<li class="li feed-li"><span class="tm num">${esc(r.time)}</span>${logo(r.pkey)}
      <div class="bd"><span class="pill pill-${r.action === 'comment' || r.action === 'reply' ? 'queue' : 'muted'}">${esc(r.action_label)}</span>
        ${r.text ? `<div class="txt">${esc(r.text)}</div>` : ''}${r.note ? `<div class="nt">${esc(r.note)}</div>` : ''}
        ${r.target ? `<div class="lk">${/^https?:/.test(r.target) ? ext(r.target, r.target.length > 70 ? r.target.slice(0, 70) + '…' : r.target) : `<span class="muted">${esc(r.target)}</span>`}</div>` : ''}</div></li>`).join('')}</ul>`
    : empty('这一天还没有互动记录。每次评论、回复、点赞后用 engage.py log 记一条，这里每分钟刷新。');
  return `${errNote(d.errors)}<div class="toolbar">${daypick(d.day, d.days)}<span class="muted small">上限来自 scripts/engage.py，回复不设上限</span></div>
    <div class="kpis" data-stagger>${kpis.map(([k, v], i) => `<div class="panel kpi"><div class="k">${k}</div><div class="v">${cnt('ek' + i, v)}</div></div>`).join('')}</div>
    <div class="sec"><div class="sec-h"><h2>各平台额度</h2><span class="meta">已用 / 每日上限，八成以上变橙，用满变红</span></div><div class="eng-grid" data-stagger>${plats}</div></div>
    <section class="panel sec"><div class="panel-h"><h2>互动流水</h2><span class="meta">最近 ${d.recent.length} 条，新的在上</span></div>${feed}</section>`;
}

/* ---------- 页面：热点 ---------- */
function renderHot(d) {
  const r = d.radar;
  const head = `<div class="toolbar">${daypick(d.day, d.days)}</div>`;
  if (!r) {
    return `${errNote(d.errors)}${head}<section class="panel">${empty(`${esc(dayLabel(d.day))}没有雷达结果。雷达在 07:00–23:30 每 30 分钟扫描一次。`)}</section>
      <section class="panel sec"><div class="panel-h"><h2>快反记录</h2></div><div class="panel-b">${d.hot_log_html ? `<div class="md">${d.hot_log_html}</div>` : empty('这一天还没有 hot-log.md。')}</div></section>`;
  }
  const fresh = d.day === todayStr() ? hotFreshness(r.candidates) : new Set();
  const srcs = Object.entries(r.source_counts || {}).map(([k, v]) => `<span class="src">${esc(k)} ${v}</span>`).join('');
  const band = `<section class="panel ver-band">
    <div><div class="k">最近一次扫描</div><div class="v num">${esc(hm(r.last_at))}</div></div>
    <div><div class="k">候选话题</div><div class="v">${cnt('h_c', r.candidates.length)}</div></div>
    <div><div class="k">本轮新抓取</div><div class="v">${cnt('h_new', r.new)}</div></div>
    <div><div class="k">抓取总数</div><div class="v">${cnt('h_total', r.total)}</div></div>
    <div><div class="k">今日扫描</div><div class="v num">${r.runs.length} 次</div></div>
    ${fresh.size ? `<div><div class="k">新上榜</div><div class="v num">${fresh.size}</div></div>` : ''}
    ${srcs ? `<div style="flex-basis:100%"><div class="k" style="margin-bottom:4px">来源</div><div class="srcs">${srcs}</div></div>` : ''}
    ${r.file !== r.last_file ? `<div class="muted small" style="flex-basis:100%">最近一次扫描（${esc(r.last_file)}）没有候选，下表来自 ${esc(hm(r.at))} 那一轮。</div>` : ''}</section>`;
  const rows = r.candidates.map((c, i) => `<tr class="${fresh.has(c.title) ? 'is-new' : ''}">
    <td class="num muted">${i + 1}</td>
    <td class="tt" style="max-width:460px"><div style="font-weight:600">${esc(c.title)} ${fresh.has(c.title) ? '<span class="tag new">新上榜</span>' : ''}</div>${c.angle ? `<div class="sub">切入：${esc(c.angle)}</div>` : ''}
      ${c.merged_titles && c.merged_titles.length > 1 ? `<div class="merged">${c.merged_titles.filter((t) => t !== c.title).slice(0, 3).map((t) => `<div>${esc(t)}</div>`).join('')}</div>` : ''}
      ${c.hot_event ? `<div class="sub">抖音热点：${esc(c.hot_event)}</div>` : ''}</td>
    <td class="r num" style="font-weight:650">${fmtN(c.score, 2)}</td>
    <td><span class="xbar">${bar((c.cross_score || 0) / 100, '', `跨平台热度 ${fmtN(c.cross_score, 1)} / 100`)}<span class="v num">${fmtN(c.cross_score, 0)}</span></span></td>
    <td><div class="srcs" style="margin:0">${(c.sources || []).map((s) => `<span class="src">${esc(s)}</span>`).join('')}</div></td>
    <td class="r">${c.risk ? `<span class="pill pill-warn">${esc(c.risk)}</span>` : '<span class="muted">—</span>'}</td>
    <td class="nowrap">${c.url ? ext(c.url, '原文') : ''}${c.zhihu_url ? ' ' + ext(c.zhihu_url, '知乎题') : ''}</td></tr>`).join('');
  const tbl = r.candidates.length ? `<div class="tbl-wrap"><table class="t"><thead><tr><th>#</th><th>话题</th><th class="r">综合分</th><th>跨平台热度</th><th>来源</th><th class="r">风险</th><th>链接</th></tr></thead><tbody data-stagger>${rows}</tbody></table></div>`
    : empty('这一轮雷达没有候选话题。');
  return `${errNote(d.errors)}${head}${band}
    <section class="panel sec"><div class="panel-h"><h2>雷达候选</h2><span class="meta">按综合分排序，来源里的 #数字 是该榜排名；2 小时内第一次出现的标「新上榜」</span></div><div class="panel-b flush">${tbl}</div></section>
    <section class="panel sec"><div class="panel-h"><h2>快反记录</h2><span class="meta">hot-log.md</span></div><div class="panel-b">${d.hot_log_html ? `<div class="md reader">${d.hot_log_html}</div>` : empty('这一天还没有快反记录。')}</div></section>`;
}

/* ---------- 页面：运营计划 ---------- */
const METRIC_CN = { bounce_2s: '2 秒跳出', completion_5s: '5 秒完播', views_lift: '播放倍数', eng_rate: '互动率', comment_rate: '评论率', follows: '涨粉', avg_view_ratio: '平均观看占比' };
const fmtMetric = (k, v) => (!isNum(v) ? '—' : ['bounce_2s', 'completion_5s', 'eng_rate', 'comment_rate', 'avg_view_ratio'].includes(k) ? pct(v, 1) : k === 'views_lift' ? v.toFixed(2) + '×' : fmtN(v, 2));
const SRC_CLS = { 用户: 's-user', 数据: 's-data', 事故: 's-incident', 运营: 's-ops' };
function renderPlan(d) {
  const v = d.version || {};
  const exps = d.experiments || [];
  const ev = d.evolve;
  const evExp = {};
  for (const e of (ev && ev.data && ev.data.experiments) || []) evExp[e.id] = e;
  const running = exps.filter((e) => ['running', 'extended'].includes(e.status));
  const changed = expChanges(exps);
  const band = `<section class="panel ver-band">
    <div><div class="k">手册版本</div><div class="v num">${v.exists ? esc(v.version || '未标版本') : '<span class="muted">尚未建立</span>'}</div></div>
    <div><div class="k">00-必读.md 更新</div><div class="v num">${v.updated ? esc(mdShort(v.updated) + ' ' + hm(v.updated)) : '—'}</div></div>
    <div><div class="k">今天升版</div><div class="v">${cnt('pv_today', (d.timeline || []).filter((t) => (t.when || '').startsWith(todayStr())).length)} 次</div></div>
    <div><div class="k">进行中的实验</div><div class="v">${cnt('pv_exp', running.length)}</div></div>
    <div><div class="k">最新数据进化</div><div class="v num">${ev ? esc(mdShort(ev.updated) + ' ' + hm(ev.updated)) : '—'}</div></div>
    <div><div class="k">近 7 天任务运行</div><div class="v">${cnt('pv_runs', (d.runs || []).length)} 次</div></div></section>`;
  const tab = S.route.q.tab || 'plan';
  const tabs = [['plan', '当前计划'], ['docs', '手册'], ['exp', '实验看板'], ['changelog', '版本时间线'], ['evolve', '数据进化'], ['runs', '任务运行']];
  const tabBar = `<div class="subtabs" role="tablist">${tabs.map(([k, n]) => `<button type="button" role="tab" data-q="tab=${k}" aria-selected="${tab === k}">${n}</button>`).join('')}</div>`;
  let body = '';
  if (tab === 'plan') {
    body = d.plan_exists ? doc(d.plan_html) : `<section class="panel">${empty('<b>运营计划尚未建立。</b>运营手册/运营计划.md 建好后这里显示全文。')}</section>`;
  } else if (tab === 'docs') {
    body = docsBlock(d);
  } else if (tab === 'exp') {
    if (!d.experiments_exists) body = `<section class="panel">${empty('<b>实验配置尚未建立。</b>config/experiments.json 建好后这里按状态分栏显示。')}</section>`;
    else {
      const col = (title, color, list) => `<div class="board-col"><h3><span class="dot" style="background:${color}"></span>${title}<span class="n">${list.length}</span></h3><div data-stagger>${list.length ? list.map((e) => expCard(e, evExp[e.id], changed.has(e.id))).join('') : '<div class="panel">' + empty('暂无') + '</div>'}</div></div>`;
      body = `<div class="board">${col('进行中', 'var(--q)', running)}${col('已暂停', 'var(--warn)', exps.filter((e) => e.status === 'paused'))}${col('已采纳', 'var(--ok)', exps.filter((e) => e.status === 'adopted'))}${col('已否决', 'var(--mute)', exps.filter((e) => e.status === 'rejected'))}</div>`;
    }
  } else if (tab === 'evolve') {
    body = evolveBlock(ev);
  } else if (tab === 'runs') {
    const runs = d.runs || [];
    body = runs.length ? `<section class="panel"><div class="tbl-wrap"><table class="t"><thead><tr><th>日期</th><th>任务</th><th>开工</th><th>收工</th><th class="r">用时</th><th>状态</th><th>手册版本</th><th>摘要</th></tr></thead>
      <tbody data-stagger>${runs.map((r) => `<tr><td class="nowrap num">${esc(mdShort(r.day + 'T'))}</td><td class="nowrap" style="font-weight:600">${esc(r.task)}</td><td class="num">${esc(hm(r.start))}</td><td class="num">${esc(hm(r.end))}</td>
        <td class="r">${isNum(r.minutes) ? r.minutes + ' 分' : '—'}</td><td>${r.state === 'done' ? pill('done', '已收工') : r.state === 'running' ? pill('queue', '进行中') : pill('warn', '未收工')}</td>
        <td class="num nowrap">${esc(r.version || '—')}</td><td style="min-width:240px">${esc(r.summary || '')}</td></tr>`).join('')}</tbody></table></div></section>`
      : `<section class="panel">${empty('近 7 天还没有任务运行记录。每个定时任务开工、收工时写入 days/&lt;日期&gt;/runs.jsonl。')}</section>`;
  } else {
    body = timelineBlock(d);
  }
  return `${errNote(d.errors)}${band}${tabBar}${body}`;
}
function docsBlock(d) {
  const ds = d.docs || {};
  if (!ds.exists) return `<section class="panel">${empty(`<b>手册目录不存在。</b>${esc(ds.manual_dir || '运营手册')}/ 建好后这里列出所有 .md。`)}</section>`;
  const cur = d.doc && d.doc.path;
  let lastDir = null;
  const list = (ds.docs || []).map((x) => {
    const head = x.dir !== lastDir ? `<div class="doc-dir">${esc(x.dir || '根目录')}</div>` : '';
    lastDir = x.dir;
    return `${head}<button type="button" data-q="doc=${esc(x.path)}" aria-pressed="${x.path === cur}" title="${esc(x.title)}">
      <span class="d">${esc(x.name)}</span><span class="s">${esc(mdShort(x.updated))} ${esc(hm(x.updated))}，${fmtN(x.size / 1000, 1)} 千字</span></button>`;
  }).join('');
  const total = (ds.docs || []).reduce((a, x) => a + x.size, 0);
  const body = d.doc && d.doc.html ? doc(d.doc.html) : `<section class="panel rep-body">${empty(d.doc && d.doc.error ? `读取失败：${esc(d.doc.error)}` : '选一份文档')}</section>`;
  return `<div class="muted small" style="margin:-6px 0 12px">${(ds.docs || []).length} 份文档，合计约 ${fmtN(total / 1000, 0)} 千字${total > 120000 ? '。<b class="bad-t">手册偏长</b>：定时任务每次开工都要读，越长越容易漏规则' : ''}</div>
    <div class="rep-layout"><nav class="panel rep-list doc-list" aria-label="手册目录">${list}</nav>${body}</div>`;
}
function timelineBlock(d) {
  const tl = d.timeline || [];
  if (!d.changelog_exists) return `<section class="panel">${empty('<b>变更日志尚未建立。</b>运营手册/变更日志.md 建好后这里显示版本时间线。')}</section>`;
  if (!tl.length) return doc(d.changelog_html);
  const items = tl.map((t, i) => `<li class="tl-item${i === 0 ? ' cur' : ''}"><span class="tl-dot"></span>
      <div class="tl-h"><span class="tl-v num">${esc(t.version || t.title)}</span>${i === 0 ? '<span class="tag">当前版本</span>' : ''}
        ${t.when ? `<span class="tl-when num">${esc(t.when)}</span>` : ''}${t.source ? `<span class="tl-src ${SRC_CLS[t.source] || ''}">来源：${esc(t.source)}</span>` : ''}</div>
      <div class="tl-body"><div class="md">${t.html}</div></div></li>`).join('');
  return `<section class="panel tl-full"><ol class="tl" data-stagger>${items}</ol></section>
    <details class="fold" style="margin-top:12px;background:var(--surface)"><summary>变更日志原文</summary><div><div class="md reader">${d.changelog_html}</div></div></details>`;
}
/* 实验状态变化：和上次看到的状态比，变了就标「状态更新」 */
function expChanges(exps) {
  const prev = store.get('exp.status', null);
  const changed = new Set();
  const next = {};
  for (const e of exps) {
    next[e.id] = e.status;
    if (prev && prev[e.id] && prev[e.id] !== e.status) changed.add(e.id);
  }
  if (!changed.size) store.set('exp.status', next);
  else setTimeout(() => store.set('exp.status', next), 30000);
  return changed;
}
function expCard(e, evx, changed) {
  const arms = e.arms || {};
  const minN = +e.min_n || 0;
  const armHtml = Object.entries(arms).map(([k, desc]) => {
    const st = evx && evx.arms && evx.arms[k];
    const n = st ? st.n || 0 : 0;
    return `<div class="arm"><span class="ab">${esc(k)}</span><span>${esc(typeof desc === 'string' ? desc : JSON.stringify(desc))}</span>
      <div class="mt">${bar(minN ? n / minN : 0, '', `样本 ${n} / 至少 ${minN || '?'} 条`)}<span class="st num">${n}/${minN || '?'} 条${st && isNum(st.value) ? `，${esc(fmtMetric(e.metric, st.value))}` : ''}</span></div></div>`;
  }).join('');
  const dir = e.direction === 'down' ? '越低越好' : e.direction === 'up' ? '越高越好' : '';
  let when = '';
  if (e.start && e.review) {
    const total = Math.max(1, daysBetween(e.start, e.review));
    const gone = Math.max(0, Math.min(total, daysBetween(e.start, todayStr())));
    const left = daysBetween(todayStr(), e.review);
    when = `<div class="when"><div class="rail" data-tip="${esc(`${e.start} 开始，${e.review} 复查`)}"><i style="width:${((gone / total) * 100).toFixed(1)}%"></i></div>
      <div class="lbl"><span>${esc(e.start.slice(5))} 开始</span><span>${left > 0 ? `还有 <b>${left}</b> 天复查` : left === 0 ? '<b>今天复查</b>' : `<b>已过复查日 ${-left} 天</b>`}</span><span>${esc(e.review.slice(5))} 复查</span></div></div>`;
  }
  const pmap = { douyin: 'dy', kuaishou: 'ks', channels: 'sph', weibo: 'wb', zhihu: 'zh', wechat: 'gzh', bilibili: 'bili', xhs: 'xhs' };
  return `<div class="panel exp${changed ? ' flash' : ''}">
    <div class="id">${esc(e.id)}${e.status === 'extended' ? '<span class="tag">已延长</span>' : ''}${changed ? '<span class="tag new">状态更新</span>' : ''}
      <span style="margin-left:auto;display:inline-flex;gap:3px">${(e.platforms || []).map((p) => logo(pmap[p] || p, 'sm')).join('')}</span></div>
    <div class="tt">${esc(e.title)}</div>
    ${e.hypothesis ? `<div class="hy">${esc(e.hypothesis)}</div>` : ''}
    <div class="arms">${armHtml}</div>${when}
    <div class="ft"><span>指标 ${esc(METRIC_CN[e.metric] || e.metric || '—')}${dir ? `（${dir}）` : ''}</span>${evx && evx.verdict ? `<span>判定：${esc(evx.verdict)}</span>` : ''}</div>
    ${e.result ? `<div class="res${e.status === 'paused' || e.status === 'rejected' ? ' warn' : ''}">${esc(e.result)}</div>` : ''}</div>`;
}
const DIM_LABEL = { dim: '维度', value: '分组', n: '条数', lift: '相对倍数', eng_rate: '互动率', n_rate: '有比率样本', bounce_2s: '2秒跳出', completion_5s: '5秒完播', views_med: '播放中位数', comments: '评论', follows: '涨粉' };
function evolveBlock(ev) {
  if (!ev) return `<section class="panel">${empty('<b>还没有数据进化结果。</b>日报任务跑 evolve.py 后写入 days/&lt;日期&gt;/evolve.json，这里显示建议和各维度对比。')}</section>`;
  const x = ev.data || {};
  if (!ev.ok) return `<section class="panel">${empty(`days/${esc(ev.day)}/evolve.json 无法解析。`)}</section>`;
  const list = (title, arr) => `<section class="panel"><div class="panel-h"><h2>${title}</h2></div><div class="panel-b">${(arr || []).length ? `<ul class="bullets">${arr.map((s) => `<li>${esc(typeof s === 'string' ? s : JSON.stringify(s))}</li>`).join('')}</ul>` : '<div class="muted small">暂无</div>'}</div></section>`;
  const dims = Array.isArray(x.dims) ? x.dims : [];
  const keys = [...new Set(dims.flatMap((r) => Object.keys(r)))];
  const fmtCell = (k, val) => {
    if (val == null) return '<span class="muted">—</span>';
    if (k === 'lift' && isNum(val)) return `<span class="${val >= 1.15 ? 'delta up' : val <= 0.85 ? 'delta down' : ''}">${val.toFixed(2)}×</span>`;
    if (['eng_rate', 'bounce_2s', 'completion_5s'].includes(k) && isNum(val)) return pct(val, 1);
    if (isNum(val)) return fmtN(val, 1);
    return esc(typeof val === 'object' ? JSON.stringify(val) : val);
  };
  const dimTbl = dims.length ? `<div class="tbl-wrap"><table class="t"><thead><tr>${keys.map((k) => `<th class="${k === 'dim' || k === 'value' ? '' : 'r'}">${esc(DIM_LABEL[k] || k)}</th>`).join('')}</tr></thead>
    <tbody>${dims.map((r, i) => `<tr ${i && dims[i - 1].dim !== r.dim ? 'style="border-top:2px solid var(--line-2)"' : ''}>${keys.map((k) => `<td class="${k === 'dim' || k === 'value' ? '' : 'r'}">${k === 'dim' && i && dims[i - 1].dim === r.dim ? '' : fmtCell(k, r[k])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`
    : empty('evolve.json 里没有 dims。');
  const base = x.platform_baseline && typeof x.platform_baseline === 'object' ? Object.entries(x.platform_baseline) : [];
  const meta = [x.window_days ? `窗口 ${x.window_days} 天` : '', isNum(x.n_posts) ? `作品 ${x.n_posts}` : '', isNum(x.n_eligible) ? `够样本 ${x.n_eligible}` : '', isNum(x.n_matched) ? `对上台账 ${x.n_matched}` : ''].filter(Boolean).join('，');
  return `<div class="muted small" style="margin:-6px 0 12px">来自 days/${esc(ev.day)}/evolve.json，生成于 ${esc(hm(x.generated || ev.updated))}${meta ? '，' + meta : ''}</div>
    <div class="grid cols-2">${list('建议', x.suggestions)}${list('数据质量', x.quality)}</div>
    ${(x.adjustments_due || []).length ? `<div class="sec">${list('到期待复查的调整', x.adjustments_due)}</div>` : ''}
    ${base.length ? `<section class="panel sec"><div class="panel-h"><h2>各平台基准</h2><span class="meta">播放/阅读中位数，用来算相对倍数</span></div><div class="panel-b"><div class="srcs">${base.map(([k, val]) => `<span class="src" style="height:24px;font-size:12px">${esc(k)} ${fmtN(val, 1)}</span>`).join('')}</div></div></section>` : ''}
    <section class="panel sec"><div class="panel-h"><h2>各维度相对表现</h2><span class="meta">相对倍数 ≥1.15 绿色，≤0.85 红色；样本少于 3 条不下结论</span></div><div class="panel-b flush">${dimTbl}</div></section>`;
}

/* ---------- 页面：日报 ---------- */
async function loadReports() {
  const list = await api('/api/reports');
  const reps = list.reports || [];
  const date = S.route.arg || (reps[0] && reps[0].date);
  let rep = null;
  if (date) {
    try { rep = await api('/api/reports/' + encodeURIComponent(date)); } catch (e) { rep = { error: e.message, date }; }
  }
  return { ...list, date, rep };
}
function renderReports(d) {
  const reps = d.reports || [];
  if (!reps.length) return errNote(d.errors) + `<section class="panel">${empty('还没有日报。日报任务每天 23:00 写入 reports/&lt;日期&gt;.md。')}</section>`;
  const list = reps.map((r) => `<button type="button" data-go="reports/${esc(r.date)}" aria-pressed="${r.date === d.date}">
    <div class="d num">${esc(dayLabel(r.date))}</div><div class="s">${r.generated ? `生成于 ${esc(r.generated)}` : ''}${r.attention ? `，${r.attention} 处需要你看` : ''}</div></button>`).join('');
  const body = d.rep && d.rep.html ? doc(d.rep.html) : `<section class="panel rep-body">${empty(`读取失败：${esc(d.rep && d.rep.error)}`)}</section>`;
  return `${errNote(d.errors)}<div class="rep-layout"><nav class="panel rep-list" aria-label="日报列表">${list}</nav>${body}</div>`;
}
function doc(html) {
  return `<div class="doc-layout"><section class="panel rep-body"><div class="md reader" data-toc>${html}</div></section><nav class="toc" aria-label="目录"></nav></div>`;
}
function buildTocs() {
  $$('#page [data-toc]').forEach((md) => {
    const lay = md.closest('.doc-layout');
    const nav = lay && $('.toc', lay);
    if (!nav) return;
    const hs = $$('h2', md);
    if (hs.length < 3) { lay.classList.add('no-toc'); return; }
    nav.innerHTML = '<div class="toc-h">目录</div>' + hs.map((h, i) => { h.id = 'sec-' + i; return `<button type="button" data-scroll="sec-${i}">${esc(h.textContent)}</button>`; }).join('');
  });
}

/* ---------- 页面表 ---------- */
const PAGE_IMPL = {
  overview: { load: () => api('/api/overview'), render: renderOverview, ctx: (d) => dayLabel(d.today) },
  growth: { load: () => api('/api/growth?days=' + encodeURIComponent(S.route.q.days || 30)), render: renderGrowth, ctx: (d) => `近 ${d.n_days} 天` },
  calendar: {
    load: async () => {
      const [cal, growth] = await Promise.all([
        api('/api/calendar' + (S.route.q.start ? '?start=' + encodeURIComponent(S.route.q.start) : '')),
        api('/api/growth?days=30'),
      ]);
      return { cal, growth };
    },
    render: renderCalendar, ctx: (d) => `${d.cal.start.slice(5).replace('-', '/')} 起的一周`,
  },
  accounts: { load: () => api('/api/accounts'), render: renderAccounts, ctx: () => '粉丝、近 7 天作品和台账' },
  content: { load: () => api('/api/content?day=' + encodeURIComponent(S.route.q.day || todayStr())), render: renderContent, ctx: (d) => dayLabel(d.day) },
  data: { load: () => api('/api/metrics?days=' + encodeURIComponent(S.route.q.days || 7)), render: renderData, ctx: (d) => `近 ${d.days} 天发布的作品` },
  engagement: { load: () => api('/api/engagement?day=' + encodeURIComponent(S.route.q.day || todayStr())), render: renderEngagement, ctx: (d) => dayLabel(d.day) },
  hot: { load: () => api('/api/hot?day=' + encodeURIComponent(S.route.q.day || todayStr())), render: renderHot, ctx: (d) => dayLabel(d.day) },
  plan: {
    load: async () => {
      const d = await api('/api/plan');
      if (S.route.q.tab === 'docs') {
        d.docs = await api('/api/docs');
        const path = S.route.q.doc || ((d.docs.docs || []).find((x) => /必读/.test(x.name)) || (d.docs.docs || [])[0] || {}).path;
        if (path) {
          try { d.doc = await api('/api/docs?path=' + encodeURIComponent(path)); } catch (e) { d.doc = { error: e.message, path }; }
        }
      }
      return d;
    },
    render: renderPlan, ctx: () => '手册、计划、实验和进化',
  },
  reports: { load: loadReports, render: renderReports, ctx: () => '每日 23:00 生成' },
};

/* ---------- 加载与刷新 ---------- */
let loadSeq = 0;
async function load(navigated) {
  const r = S.route;
  const impl = PAGE_IMPL[r.page];
  const seq = ++loadSeq;
  const page = $('#page');
  const name = PAGES.find((p) => p.id === r.page).name;
  $('#pageTitle').textContent = name;
  document.title = `${name} · ${(S.meta && S.meta.title) || '运营工作台'}`;
  setSpinning(true);
  loadHealth();
  let skTimer = null;
  if (navigated) {
    window.scrollTo(0, 0);
    // 数据 120ms 内回来就直接出内容，避免骨架屏一闪
    skTimer = setTimeout(() => {
      if (seq !== loadSeq) return;
      disposeCharts(page);
      page.innerHTML = skeleton(r.page);
      page.dataset.page = '';
      Motion.fade(page, 200);
    }, 120);
  }
  let d;
  try {
    d = await impl.load();
  } catch (e) {
    clearTimeout(skTimer);
    if (seq !== loadSeq) return;
    setSpinning(false);
    setRefresh(false, e.message);
    if (navigated || !page.dataset.page) {
      disposeCharts(page);
      page.innerHTML = `<section class="panel">${empty(`<b>读取失败：${esc(e.message)}</b><br>确认本地服务还在运行（<code>python dashboard/server.py</code>），然后点右上角刷新。`)}</section>`;
    }
    return;
  }
  clearTimeout(skTimer);
  if (seq !== loadSeq) return;
  const samePage = page.dataset.page === r.page && !navigated;
  const prevNums = samePage ? Motion.snapshot(page) : null;
  const prevPending = new Set($$('[data-pid]', page).map((el) => el.dataset.pid));
  const keepOpen = {};
  $$('#page details[data-k-open]').forEach((el) => { keepOpen[el.dataset.kOpen] = el.open; });
  const keepScroll = {};
  $$('#page [data-keep-scroll]').forEach((el) => { keepScroll[el.dataset.keepScroll] = el.scrollLeft; });
  disposeCharts(page);
  EC.specs = [];
  S.data[r.page] = d;
  page.innerHTML = impl.render(d);
  page.dataset.page = r.page;
  $('#pageCtx').textContent = impl.ctx ? impl.ctx(d) : '';
  $$('#page details[data-k-open]').forEach((el) => { if (keepOpen[el.dataset.kOpen]) el.open = true; });
  $$('#page [data-keep-scroll]').forEach((el) => {
    if (keepScroll[el.dataset.keepScroll] != null) el.scrollLeft = keepScroll[el.dataset.keepScroll];
    else if (el.dataset.keepScroll === 'rundown') centerNow(el);
  });
  $$('#page .md a').forEach((a) => { a.target = '_blank'; a.rel = 'noopener noreferrer'; });
  buildTocs();
  const entering = !samePage;
  mountCharts(page, entering);
  if (entering) {
    Motion.enter(page);
    Motion.bars(page);
    if ($('[data-rundown]', page)) Motion.rundown(page);
    $$('#page .acc-list, #page .rep-list').forEach((list) => {
      const b = $('[aria-pressed="true"]', list);
      if (b && list.scrollWidth > list.clientWidth) list.scrollLeft = b.offsetLeft - (list.clientWidth - b.offsetWidth) / 2;
    });
  } else {
    // 自动刷新：新出现的待处理行闪一下
    $$('[data-pid]', page).forEach((el) => { if (prevPending.size && !prevPending.has(el.dataset.pid)) el.classList.add('flash'); });
  }
  Motion.counts(page, prevNums, entering);
  if (S.ui.filter.content && r.page === 'content') applyFilter(S.ui.filter.content);
  if (S.ui.filter.posts && r.page === 'data') applyFilter(S.ui.filter.posts);
  // 地址里带着 item（收藏或分享的链接）就打开那条内容
  if (r.q.item && S.drawerId !== r.q.item) openDrawer(r.q.item);
  else if (S.drawerId) S.drawerList = collectItems().includes(S.drawerId) ? collectItems() : S.drawerList;
  S.lastOk = new Date();
  setSpinning(false);
  setRefresh(true);
}
function centerNow(el) {
  const now = $('.rd-now', el), layer = $('.rd-now-layer', el), lab = $('.rd-lab', el);
  if (now && layer && lab && el.scrollWidth > el.clientWidth) {
    const labW = lab.getBoundingClientRect().width;
    el.scrollLeft = Math.max(0, layer.offsetLeft + now.offsetLeft - labW - (el.clientWidth - labW) / 2);
  }
}
function rerender() {
  const r = S.route;
  const d = S.data[r.page];
  if (!d) return;
  const page = $('#page');
  const keepScroll = {};
  $$('[data-keep-scroll]', page).forEach((el) => { keepScroll[el.dataset.keepScroll] = el.scrollLeft; });
  disposeCharts(page);
  EC.specs = [];
  page.innerHTML = PAGE_IMPL[r.page].render(d);
  $$('[data-keep-scroll]', page).forEach((el) => { if (keepScroll[el.dataset.keepScroll] != null) el.scrollLeft = keepScroll[el.dataset.keepScroll]; });
  buildTocs();
  mountCharts(page, false);
  if (S.ui.filter.content && r.page === 'content') applyFilter(S.ui.filter.content);
  if (S.ui.filter.posts && r.page === 'data') applyFilter(S.ui.filter.posts);
}
function setSpinning(on) { $('#refreshBtn').classList.toggle('spinning', on && !RM.matches); }
function setRefresh(ok, msg) {
  const t = (S.lastOk || new Date()).toLocaleTimeString('zh-CN', { hour12: false });
  const el = $('#lastRefresh');
  if (ok) el.innerHTML = `<span class="refresh-dot"></span><span class="lr-label">最后刷新 </span><span class="num">${t}</span>`;
  else el.innerHTML = `<span class="refresh-dot err"></span>刷新失败${S.lastOk ? `<span class="lr-label">，显示的是 <span class="num">${t}</span> 的数据</span>` : ''}`;
  el.title = ok ? '每 60 秒自动刷新' : (msg || '');
}

/* ---------- 导航（侧栏 + 手机底栏） ---------- */
function renderNav() {
  const badge = S.pendingCount ? `<span class="badge num" aria-label="${S.pendingCount} 条待处理">${S.pendingCount}</span>` : '';
  $('#navLinks').innerHTML = PAGES.map((p) => `<a href="#/${p.id}" ${S.route.page === p.id ? 'aria-current="page"' : ''} title="${esc(PAGE_DESC[p.id] || '')}（${p.key}）">${ico(p.id)}<span class="lb">${p.name}</span>${p.id === 'overview' ? badge : `<kbd class="nk">${p.key}</kbd>`}</a>`).join('');
  const inMore = !MOBILE_MAIN.includes(S.route.page);
  $('#bnav').innerHTML = MOBILE_MAIN.map((id) => {
    const p = PAGES.find((x) => x.id === id);
    return `<a href="#/${id}" ${S.route.page === id ? 'aria-current="page"' : ''}>${ico(id)}<span>${p.name}</span>${id === 'overview' ? badge : ''}</a>`;
  }).join('') + `<button type="button" data-more ${inMore ? 'aria-current="page"' : ''} aria-expanded="false" aria-controls="sheet">${ico('more')}<span>${inMore ? PAGES.find((x) => x.id === S.route.page).name : '更多'}</span></button>`;
  $('#sheet').innerHTML = PAGES.filter((p) => !MOBILE_MAIN.includes(p.id)).map((p) => `<a href="#/${p.id}" ${S.route.page === p.id ? 'aria-current="page"' : ''}>${ico(p.id)}<span>${p.name}</span><span class="ds">${esc(PAGE_DESC[p.id] || '')}</span></a>`).join('')
    + (S.meta && S.meta.auth ? `<a href="/auth/logout">${ico('left')}<span>退出登录</span><span class="ds">${esc(S.meta.user || '')}</span></a>` : '');
}
/* 侧栏选中块滑到当前项 */
function movePill(animate) {
  const pill = $('#navPill');
  const cur = $('#nav a[aria-current]');
  if (!pill || !cur) return;
  if (!animate) pill.style.transition = 'none';
  pill.style.transform = `translateY(${cur.offsetTop}px)`;
  pill.style.height = cur.offsetHeight + 'px';
  if (!animate) { void pill.offsetWidth; pill.style.transition = ''; }
}
function updateBadge(n) {
  if (S.pendingCount !== n) {
    const grew = n > S.pendingCount && S.rendered;
    S.pendingCount = n;
    renderNav();
    movePill(false);
    if (grew) $$('.badge').forEach((b) => { b.classList.remove('ring'); void b.offsetWidth; b.classList.add('ring'); });
  }
  S.rendered = true;
}
function paintBrand(accs) {
  $('#brandMark').innerHTML = (accs || []).slice(0, 8).map((a) => `<i style="background:var(--p-${PLAT[a.pkey] ? a.pkey : 'other'})" title="${esc(a.name)}"></i>`).join('');
}
function openSheet() { $('#sheet').classList.add('open'); $('#scrim').classList.add('open'); $('[data-more]')?.setAttribute('aria-expanded', 'true'); }
function closeSheet() { $('#sheet').classList.remove('open'); if (!S.drawerId) $('#scrim').classList.remove('open'); $('[data-more]')?.setAttribute('aria-expanded', 'false'); }

/* ---------- 元信息、主题、数据源状态 ---------- */
async function loadMeta() {
  try {
    S.meta = await api('/api/meta');
  } catch { S.meta = null; return; }
  const m = S.meta;
  $('#brandName').textContent = m.title || '运营工作台';
  $('#brandSub').textContent = m.subtitle || '';
  $('#sideVer').textContent = m.auth ? `v${m.version} · ${location.host}` : `v${m.version} · ${m.host}:${m.port}`;
  if (m.auth) {
    $('#sideFoot').insertAdjacentHTML('beforeend', `<div class="small">已登录 ${esc(m.user || '')} · <a href="/auth/logout">退出</a></div>`);
    const lr = $('#sideFoot div');
    if (lr) lr.textContent = '只读看板，数据每小时从本机同步一次';
  }
  $('#demoBadge').hidden = !m.demo;
  paintBrand(m.accounts);
  renderNav();
  movePill(false);
}
const THEMES = ['system', 'light', 'dark'];
const THEME_CN = { system: '跟随系统', light: '浅色', dark: '深色' };
function applyTheme(th, announce) {
  if (th === 'light' || th === 'dark') document.documentElement.dataset.theme = th;
  else delete document.documentElement.dataset.theme;
  store.set('theme', th === 'system' ? null : th);
  const icon = th === 'dark' ? 'moon' : th === 'light' ? 'sun' : 'system';
  $('#themeBtn').innerHTML = ico(icon);
  $('#themeBtn').title = `当前：${THEME_CN[th]}（T 切换）`;
  if (announce) {
    toast(`界面：${THEME_CN[th]}`);
    rerender();
    if (S.drawerId) openDrawer(S.drawerId, { keepList: true });
  }
}
function cycleTheme() {
  const cur = store.get('theme', null) || 'system';
  applyTheme(THEMES[(THEMES.indexOf(cur) + 1) % THEMES.length], true);
}
async function loadHealth() {
  try { S.health = await api('/api/health'); } catch { return; }
  const h = S.health;
  const bad = h.sources.filter((x) => x.state !== 'ok');
  const chip = $('#healthChip');
  chip.hidden = false;
  chip.className = 'hchip' + (bad.length ? ' warn' : '');
  chip.innerHTML = `<span class="dot"></span><span class="lb">${bad.length ? `${bad.length} 个数据源要看` : '数据源正常'}</span>`;
  chip.title = bad.map((x) => `${x.label}：${x.state === 'missing' ? '没有数据' : ago(x.age_min) + '更新'}`).join('\n') || '所有数据源都在按节奏更新';
  if (!$('#healthPop').hidden) renderHealthPop();
}
function renderHealthPop() {
  const h = S.health;
  if (!h) return;
  $('#healthPop').innerHTML = `<div class="hp-h"><b>数据源</b><span class="muted small">工作台只读这些文件，过期说明对应的定时任务没跑或跑失败了</span></div>
    ${h.sources.map((x) => `<div class="hp-row ${x.state}"><span class="dot"></span><div><div class="hp-t">${esc(x.label)}<span class="muted small">${x.key === 'manual' ? '' : x.state === 'missing' ? '没有数据' : esc(ago(x.age_min)) + '更新'}${x.expect_min && x.key !== 'manual' ? `，预期 ${x.expect_min >= 120 ? Math.round(x.expect_min / 60) + ' 小时' : x.expect_min + ' 分钟'}内` : ''}</span></div>
      <div class="hp-d">${esc(x.hint)}</div></div></div>`).join('')}`;
}
function toggleHealth(force) {
  const pop = $('#healthPop');
  const open = force != null ? force : pop.hidden;
  pop.hidden = !open;
  $('#healthChip').setAttribute('aria-expanded', String(open));
  if (open) renderHealthPop();
}

/* ---------- 命令面板（⌘K） ---------- */
const PAL = { items: [], idx: 0, seq: 0, timer: null };
function palStatic(q) {
  const k = q.trim().toLowerCase();
  const hit = (s) => !k || String(s).toLowerCase().includes(k);
  const out = [];
  PAGES.forEach((p) => { if (hit(p.name) || hit(p.id) || hit(PAGE_DESC[p.id] || '')) out.push({ sec: '页面', icon: p.id, title: p.name, sub: PAGE_DESC[p.id], key: p.key, run: () => go(p.id) }); });
  ((S.meta && S.meta.accounts) || []).forEach((a) => { if (k && (hit(a.name) || hit(a.platform))) out.push({ sec: '账号', pk: a.pkey, title: a.name, sub: a.platform, run: () => go('accounts', a.slot) }); });
  const acts = [
    { title: '刷新当前页', sub: '重新读取数据', key: 'R', icon: 'more', run: () => load(false), words: 'refresh 刷新' },
    { title: '切换深浅色', sub: '跟随系统 → 浅色 → 深色', key: 'T', icon: 'moon', run: cycleTheme, words: 'theme 主题 深色 浅色 暗色' },
    { title: '复制当前页地址', sub: '含筛选条件和打开的内容', icon: 'link', run: () => copyText(location.href, '地址'), words: 'copy link 链接 分享' },
    { title: '数据源状态', sub: '各数据最后更新时间', icon: 'bolt', run: () => toggleHealth(true), words: 'health 健康 数据源' },
    { title: '今天的内容', sub: '内容页，今天', icon: 'content', run: () => go('content', null, { day: todayStr() }), words: 'today 今天 内容' },
    { title: '今天失败的发布', sub: '内容页，只看失败', icon: 'content', run: () => go('content', null, { day: todayStr(), status: 'fail' }), words: 'fail 失败' },
    { title: '运营手册', sub: '浏览全部 .md', icon: 'doc', run: () => go('plan', null, { tab: 'docs' }), words: 'manual docs 手册 规则' },
    { title: '键盘快捷键', sub: '全部快捷键', key: '?', icon: 'keyboard', run: openHelp, words: 'help shortcut 快捷键 帮助' },
  ];
  if (S.meta && S.meta.auth) acts.push({ title: '退出登录', sub: S.meta.user || '', icon: 'left', run: () => { location.href = '/auth/logout'; }, words: 'logout 退出 登出' });
  acts.forEach((a) => { if (k && (hit(a.title) || hit(a.words))) out.push({ sec: '操作', ...a }); });
  if (!k) out.push(...acts.slice(0, 4).map((a) => ({ sec: '操作', ...a })));
  const recent = store.get('recent', []);
  if (!k && recent.length) out.push(...recent.slice(0, 5).map((r) => ({ sec: '最近打开', pk: r.pkey, title: r.title, sub: `${r.account || ''} ${r.day || ''}`, run: () => openDrawer(r.id) })));
  return out;
}
function rememberRecent(i) {
  const r = store.get('recent', []).filter((x) => x.id !== i.id);
  r.unshift({ id: i.id, title: i.title, pkey: i.pkey, account: i.account_name, day: i.day });
  store.set('recent', r.slice(0, 12));
}
function palRender() {
  const list = $('#palList');
  if (!PAL.items.length) { list.innerHTML = `<div class="pal-empty">${PAL.loading ? '正在搜索…' : '没有找到。试试换个关键词，内容按标题搜索。'}</div>`; return; }
  let sec = null;
  list.innerHTML = PAL.items.map((it, i) => {
    const head = it.sec !== sec ? `<div class="pal-sec">${esc(it.sec)}</div>` : '';
    sec = it.sec;
    const lead = it.pk ? logo(it.pk) : it.thumb ? `<img src="${esc(it.thumb)}" alt="" loading="lazy">` : ico(it.icon || 'doc');
    return `${head}<div class="pal-it" role="option" id="pal-${i}" aria-selected="${i === PAL.idx}" data-pal="${i}"><span class="ld">${lead}</span>
      <span class="tx"><span class="t1">${esc(it.title)}</span>${it.sub ? `<span class="t2">${esc(it.sub)}</span>` : ''}</span>${it.badge || ''}${it.key ? `<kbd>${esc(it.key)}</kbd>` : ''}</div>`;
  }).join('');
  $('#palInput').setAttribute('aria-activedescendant', 'pal-' + PAL.idx);
  $(`#pal-${PAL.idx}`)?.scrollIntoView({ block: 'nearest' });
}
function palQuery(q) {
  PAL.items = palStatic(q);
  PAL.idx = 0;
  const k = q.trim();
  clearTimeout(PAL.timer);
  if (k.length < 1) { PAL.loading = false; palRender(); return; }
  PAL.loading = true;
  palRender();
  const seq = ++PAL.seq;
  PAL.timer = setTimeout(async () => {
    let res;
    try { res = await api('/api/search?q=' + encodeURIComponent(k)); } catch { res = { items: [], reports: [], docs: [] }; }
    if (seq !== PAL.seq) return;
    PAL.loading = false;
    const more = [];
    res.items.forEach((i) => more.push({ sec: '内容', pk: i.pkey, thumb: null, title: i.title || '（无标题）', sub: `${i.account_name || i.platform_name || ''} · ${mdShort(i.day)} ${i.time || ''}${i.column ? ' · ' + i.column : ''}`,
      badge: pill(i.superseded_by ? 'muted' : i.bucket, i.superseded_by ? '已重提' : i.status_label), run: () => openDrawer(i.id) }));
    res.reports.forEach((r) => more.push({ sec: '日报', icon: 'reports', title: dayLabel(r.date) + ' 日报', sub: r.snippet, run: () => go('reports', r.date) }));
    res.docs.forEach((x) => more.push({ sec: '手册', icon: 'doc', title: x.title, sub: `${x.path}${x.snippet ? ' · ' + x.snippet : ''}`, run: () => go('plan', null, { tab: 'docs', doc: x.path }) }));
    PAL.items = [...palStatic(q), ...more];
    palRender();
  }, 160);
}
function openPalette() {
  const p = $('#palette');
  if (!p.hidden) return;
  PAL.ret = document.activeElement;
  p.hidden = false;
  const inp = $('#palInput');
  inp.value = '';
  palQuery('');
  inp.focus();
  if (canMove()) $('.pal-box', p).animate({ opacity: [0, 1], translate: ['0 -6px', '0 0'], scale: [0.98, 1] }, { duration: 180, easing: EASE_OUT });
}
function closePalette() {
  const p = $('#palette');
  if (p.hidden) return;
  p.hidden = true;
  clearTimeout(PAL.timer);
  PAL.seq++;
  if (PAL.ret && PAL.ret.focus && PAL.ret.isConnected) PAL.ret.focus();
}
function palRun(i) {
  const it = PAL.items[i];
  if (!it) return;
  closePalette();
  it.run();
}

/* ---------- 快捷键帮助 ---------- */
const KEYS = [
  ['⌘K / Ctrl+K / /', '搜索、跳转'], ['1–9、0', '切换页面（按侧栏顺序）'], ['R', '刷新当前页'], ['T', '切换深浅色'],
  ['[ / ]', '前一天 / 后一天（日历页是前后一周）'], ['← / →', '内容详情里看上一条 / 下一条'], ['C', '内容详情里复制标题'], ['O', '内容详情里打开原帖'],
  ['Esc', '关闭弹窗、抽屉'], ['?', '打开这张表'],
];
function openHelp() {
  const m = $('#helpModal');
  m.innerHTML = `<div class="modal-box"><div class="modal-h"><b>键盘快捷键</b><button class="btn ghost" type="button" data-close-modal>关闭</button></div>
    <dl class="keys">${KEYS.map(([k, v]) => `<dt>${k.split(' / ').map((x) => `<kbd>${esc(x)}</kbd>`).join(' ')}</dt><dd>${esc(v)}</dd>`).join('')}</dl>
    <div class="muted small" style="margin-top:12px">在输入框里打字时，单键快捷键不生效。</div></div>`;
  m.hidden = false;
  $('[data-close-modal]', m).focus();
}
function closeHelp() { $('#helpModal').hidden = true; }

/* ---------- 事件 ---------- */
document.addEventListener('click', (ev) => {
  const t = ev.target;
  if (t.closest('[data-stop]')) return;
  if (t.closest('[data-palette]')) { openPalette(); return; }
  const pi = t.closest('[data-pal]');
  if (pi) { palRun(+pi.dataset.pal); return; }
  if (t.id === 'palette') { closePalette(); return; }
  if (t.closest('[data-help]')) { openHelp(); return; }
  if (t.closest('[data-close-modal]') || t.id === 'helpModal') { closeHelp(); return; }
  if (t.closest('#healthChip')) { toggleHealth(); return; }
  if (!t.closest('#healthPop') && !$('#healthPop').hidden) toggleHealth(false);
  if (t.closest('[data-more]')) { $('#sheet').classList.contains('open') ? closeSheet() : openSheet(); return; }
  if (t.closest('#sheet a')) { closeSheet(); return; }
  if (t.closest('[data-close]') || t.id === 'scrim') { if (S.drawerId) closeDrawer(); else closeSheet(); return; }
  const stp = t.closest('[data-dstep]');
  if (stp && !stp.disabled) { stepDrawer(+stp.dataset.dstep); return; }
  const cp = t.closest('[data-copy]');
  if (cp && S.drawerData) {
    const d = S.drawerData, it = d.item;
    const map = { title: [it.title, '标题'], desc: [d.description, '文案'], url: [it.url, '链接'], share: [location.href, '本页地址'] };
    const [v, w] = map[cp.dataset.copy] || [];
    copyText(v, w);
    return;
  }
  const csv = t.closest('[data-csv]');
  if (csv) { exportCSV(csv.dataset.csv); return; }
  const vw = t.closest('[data-view]');
  if (vw) { store.set('content.view', vw.dataset.view); rerender(); Motion.enter($('#page .cgrid')?.parentElement || $('#page')); return; }
  const hb = t.closest('[data-hb]');
  if (hb) { go('content', null, { day: hb.dataset.hb }); return; }
  const item = t.closest('[data-item]');
  if (item) { ev.preventDefault(); openDrawer(item.dataset.item); return; }
  const g = t.closest('[data-go]');
  if (g) {
    const [path, qs] = g.dataset.go.split('?');
    const [page, arg] = path.split('/');
    go(page, arg, Object.fromEntries(new URLSearchParams(qs || '')));
    return;
  }
  const q = t.closest('[data-q]');
  if (q) { const s = q.dataset.q, ix = s.indexOf('='); setQ({ [s.slice(0, ix)]: s.slice(ix + 1) }); return; }
  const dayBtn = t.closest('[data-day]');
  if (dayBtn && !dayBtn.disabled) { setQ({ day: dayBtn.dataset.day }); return; }
  const sc = t.closest('[data-scroll]');
  if (sc) { const el = document.getElementById(sc.dataset.scroll); if (el) el.scrollIntoView({ behavior: RM.matches ? 'auto' : 'smooth', block: 'start' }); return; }
  const tab = t.closest('[data-tab]');
  if (tab) { const [k, v] = tab.dataset.tab.split(':'); S.ui.tab[k] = v; rerender(); return; }
  const thx = t.closest('th[data-sort]');
  if (thx) { sortBy(thx.dataset.sort); return; }
  const tog = t.closest('tr[data-toggle]');
  if (tog && !t.closest('a')) { S.ui.openTips[tog.dataset.toggle] = !S.ui.openTips[tog.dataset.toggle]; rerender(); }
});
function exportCSV(kind) {
  const r = S.route;
  if (kind === 'posts' && S.data.data) {
    const rows = S.data.data.rows;
    downloadCSV(`作品明细-近${S.data.data.days}天-${todayStr()}.csv`,
      ['平台', '账号', '发布时间', '标题', '栏目', '播放/阅读', '赞', '藏', '评', '转', '涨粉', '2秒跳出', '5秒完播', '平均观看占比', '时长秒', '诊断'],
      rows.map((x) => [x.platform_name, x.account_name, (x.created_iso || '').replace('T', ' ').slice(0, 16), x.title, x.column, x.views, x.likes, x.favorites, x.comments, x.shares, x.follows,
        x.bounce_2s, x.completion_5s, x.avg_view_ratio, x.duration, (x.tips || []).join('；')]));
  } else if (kind === 'roi' && S.data.growth) {
    const d = S.data.growth;
    downloadCSV(`投入产出-近${d.n_days}天-${todayStr()}.csv`,
      ['账号', '平台', '粉丝', '净增', '每条涨粉', '每千播放涨粉', '发出', '应发', '失败', '均播放', '互动率', '作品涨粉'],
      d.roi.map((x) => [x.name, x.platform, x.fans, x.gain, x.gain_per_post, x.gain_per_k_views, x.posts, x.expected, x.fails, x.views_per_post, x.inter_rate, x.follows]));
  } else toast('这一页没有可导出的表');
  void r;
}
document.addEventListener('input', (ev) => {
  const t = ev.target;
  if (t.id === 'palInput') { palQuery(t.value); return; }
  if (t.matches('[data-filter]')) { S.ui.filter[t.dataset.filter] = t.value; applyFilter(t.value); }
});
const typing = (el) => el && (el.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName));
document.addEventListener('keydown', (ev) => {
  const k = ev.key;
  // 命令面板
  if ((ev.metaKey || ev.ctrlKey) && k.toLowerCase() === 'k') { ev.preventDefault(); $('#palette').hidden ? openPalette() : closePalette(); return; }
  if (!$('#palette').hidden) {
    if (k === 'Escape') { ev.preventDefault(); closePalette(); }
    else if (k === 'ArrowDown') { ev.preventDefault(); PAL.idx = Math.min(PAL.items.length - 1, PAL.idx + 1); palRender(); }
    else if (k === 'ArrowUp') { ev.preventDefault(); PAL.idx = Math.max(0, PAL.idx - 1); palRender(); }
    else if (k === 'Enter') { ev.preventDefault(); palRun(PAL.idx); }
    return;
  }
  if (!$('#helpModal').hidden) { if (k === 'Escape' || k === '?') { ev.preventDefault(); closeHelp(); } return; }
  if (k === 'Escape') {
    if (!$('#healthPop').hidden) toggleHealth(false);
    else if (S.drawerId) closeDrawer();
    else closeSheet();
    return;
  }
  if ((k === 'Enter' || k === ' ') && ev.target.matches && ev.target.matches('th[data-sort]')) { ev.preventDefault(); sortBy(ev.target.dataset.sort); return; }
  if (ev.metaKey || ev.ctrlKey || ev.altKey || typing(ev.target)) return;
  if (S.drawerId) {
    if (k === 'ArrowLeft' || k === 'k') { ev.preventDefault(); stepDrawer(-1); return; }
    if (k === 'ArrowRight' || k === 'j') { ev.preventDefault(); stepDrawer(1); return; }
    if (k === 'c' && S.drawerData) { copyText(S.drawerData.item.title, '标题'); return; }
    if (k === 'o' && S.drawerData && S.drawerData.item.url) { window.open(S.drawerData.item.url, '_blank', 'noopener'); return; }
  }
  if (k === '/') { ev.preventDefault(); openPalette(); return; }
  if (k === '?') { ev.preventDefault(); openHelp(); return; }
  if (k === 'r' || k === 'R') { load(false); return; }
  if (k === 't' || k === 'T') { cycleTheme(); return; }
  const pg = PAGES.find((p) => p.key === k);
  if (pg && !S.drawerId) { go(pg.id); return; }
  if (k === '[' || k === ']') {
    const step = k === '[' ? -1 : 1;
    const r = S.route;
    if (r.page === 'calendar' && S.data.calendar) { setQ({ start: shiftDay(S.data.calendar.cal.start, 7 * step) }); return; }
    if (['content', 'engagement', 'hot'].includes(r.page)) {
      const cur = r.q.day || todayStr();
      const nx = shiftDay(cur, step);
      if (nx <= todayStr()) setQ({ day: nx });
    }
  }
});
document.addEventListener('change', (ev) => {
  const t = ev.target;
  if (t.matches('[data-dayselect]')) setQ({ day: t.value });
  if (t.matches('[data-qselect]')) setQ({ [t.dataset.qselect]: t.value });
});

/* 提示框（非图表元素用；图表用 ECharts 自带 tooltip） */
const tip = $('#tip');
let tipEl = null;
document.addEventListener('mouseover', (ev) => {
  const el = ev.target.closest && ev.target.closest('[data-tip]');
  if (el === tipEl) return;
  tipEl = el;
  if (!el) { tip.classList.remove('on'); return; }
  tip.textContent = el.dataset.tip;
  tip.classList.add('on');
});
document.addEventListener('mousemove', (ev) => {
  if (!tipEl) return;
  const r = tip.getBoundingClientRect();
  let x = ev.clientX + 14, y = ev.clientY + 14;
  if (x + r.width > innerWidth - 8) x = ev.clientX - r.width - 14;
  if (y + r.height > innerHeight - 8) y = ev.clientY - r.height - 14;
  tip.style.left = Math.max(8, x) + 'px';
  tip.style.top = Math.max(8, y) + 'px';
});
document.addEventListener('focusin', (ev) => {
  const el = ev.target.closest && ev.target.closest('[data-tip]');
  if (!el) { tip.classList.remove('on'); tipEl = null; return; }
  tipEl = el;
  tip.textContent = el.dataset.tip;
  const b = el.getBoundingClientRect();
  tip.classList.add('on');
  tip.style.left = Math.min(innerWidth - 300, Math.max(8, b.left)) + 'px';
  tip.style.top = b.bottom + 8 + 'px';
});

window.addEventListener('scroll', () => { $('#topbar').classList.toggle('scrolled', window.scrollY > 4); }, { passive: true });
window.addEventListener('resize', () => movePill(false));
window.addEventListener('hashchange', () => {
  const prev = S.route;
  const next = parseHash();
  // 只有 item 变了（例如浏览器后退到打开抽屉前）：只开关抽屉，不重新加载页面
  const strip = (q) => { const { item, ...rest } = q; return JSON.stringify(rest); };
  if (prev.page === next.page && prev.arg === next.arg && strip(prev.q) === strip(next.q)) {
    S.route = next;
    if (next.q.item && next.q.item !== S.drawerId) openDrawer(next.q.item);
    else if (!next.q.item && S.drawerId) closeDrawer();
    return;
  }
  if (S.drawerId) closeDrawer();
  closeSheet();
  closePalette();
  toggleHealth(false);
  S.route = next;
  renderNav();
  requestAnimationFrame(() => movePill(true));
  load(true);
});
$('#refreshBtn').addEventListener('click', () => load(false));
$('#themeBtn').addEventListener('click', cycleTheme);
document.addEventListener('visibilitychange', () => {
  if (!document.hidden && S.lastOk && Date.now() - S.lastOk.getTime() > 60000) load(false);
});
setInterval(() => { if (!document.hidden && $('#palette').hidden) load(false); }, 60000);
/* 系统切换深浅色时，图表按新配色重画（不重放动画） */
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { rerender(); if (S.drawerId) openDrawer(S.drawerId, { keepList: true }); });

/* 启动 */
(async () => {
  $('#kbdHint').textContent = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent) ? '⌘K' : 'Ctrl K';
  applyTheme(store.get('theme', null) || 'system', false);
  S.route = parseHash();
  renderNav();
  movePill(false);
  paintBrand(['dy', 'sph', 'bili', 'ks', 'xhs', 'wb', 'zh', 'gzh'].map((pkey) => ({ pkey, name: PLAT[pkey].name })));
  await loadMeta();
  load(true);
  if (S.route.page !== 'overview') {
    api('/api/overview').then((d) => updateBadge(d.pending.length)).catch(() => {});
  }
})();
