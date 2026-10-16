// 微博自己的博文数据（在已登录 weibo.com 的标签页里用 javascript_tool 执行）。reads_count 是阅读数（只有自己看得到）。
// 账号「示例作者」uid=demo-weibo-uid；换账号改 UID。返回 {platform, at, f, rows}。存成 days/<日期>/metrics/weibo-<账号>.json → metrics.py ingest weibo <账号> <文件>
await (async () => {
  const UID = 'demo-weibo-uid';
  const F = ['id', 'created', 'title', 'views', 'likes', 'comments', 'shares', 'pics'];
  const rows = [];
  const since = Date.now() / 1000 - 45 * 86400;
  for (let page = 1; page <= 3; page++) {
    const r = await fetch(`/ajax/statuses/mymblog?uid=${UID}&page=${page}&feature=0`, { credentials: 'include', headers: { 'x-requested-with': 'XMLHttpRequest' } });
    const j = await r.json();
    const list = (j.data || {}).list || [];
    if (!list.length) break;
    let old = false;
    for (const x of list) {
      const ts = Math.round(new Date(x.created_at).getTime() / 1000);
      if (ts < since) { old = true; continue; }
      if (x.retweeted_status) continue;  // 转发的不算作品
      rows.push([x.idstr, ts, (x.text_raw || '').replace(/\s+/g, ' ').slice(0, 40), +x.reads_count || 0, +x.attitudes_count || 0, +x.comments_count || 0, +x.reposts_count || 0, +x.pic_num || 0]);
    }
    if (old) break;
  }
  return JSON.stringify({ platform: 'weibo', at: Math.round(Date.now() / 1000), f: F, rows });
})()
