// 小红书创作服务平台笔记数据（在已登录 creator.xiaohongshu.com/new/note-manager 的标签页里用 javascript_tool 执行）
// 小红书接口要页面自己算签名，外部 fetch 会 406；所以挂 XHR 钩子，点「已发布」「全部」让页面自己请求，再从钩子里取响应。
// 返回 {platform, at, f, rows}，不含链接/令牌。存成 days/<日期>/metrics/xhs-<账号>.json → metrics.py ingest xhs <账号> <文件>
await (async () => {
  if (!location.pathname.includes('note-manager')) return JSON.stringify({ error: '先打开 creator.xiaohongshu.com/new/note-manager' });
  window.__xhsCap = [];
  const X = XMLHttpRequest.prototype;
  if (!X.__xhsHooked) {
    const oo = X.open, os = X.send;
    X.open = function (m, u) { this.__u = String(u); return oo.apply(this, arguments); };
    X.send = function () {
      this.addEventListener('load', () => {
        if (/note\/user\/posted/.test(this.__u)) { try { window.__xhsCap.push(JSON.parse(this.responseText)); } catch (e) {} }
      });
      return os.apply(this, arguments);
    };
    X.__xhsHooked = true;
  }
  const leaf = t => [...document.querySelectorAll('*')].find(e => e.children.length === 0 && t.test(e.textContent.trim()));
  for (const t of [/^已发布/, /^全部/]) { const el = leaf(t); el && el.click(); await new Promise(r => setTimeout(r, 3000)); }
  const seen = new Set(), rows = [];
  const F = ['id', 'created', 'title', 'type', 'views', 'likes', 'comments', 'favorites', 'shares'];
  for (const j of window.__xhsCap) {
    for (const n of ((j.data || {}).notes || [])) {
      if (seen.has(n.id) || n.schedule_post_time) continue;  // 定时未发的跳过
      seen.add(n.id);
      const ts = Math.round(new Date((n.time || '').replace(' ', 'T') + '+08:00').getTime() / 1000) || 0;
      rows.push([n.id, ts, (n.display_title || '').slice(0, 40), n.type, +n.view_count || 0, +n.likes || 0, +n.comments_count || 0, +n.collected_count || 0, +n.shared_count || 0]);
    }
  }
  return JSON.stringify({ platform: 'xhs', at: Math.round(Date.now() / 1000), f: F, rows });
})()
