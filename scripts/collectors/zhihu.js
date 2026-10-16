// 知乎创作中心内容数据（在已登录 www.zhihu.com 的标签页里用 javascript_tool 执行）。回答/文章/想法/视频都在 creations/v2/all 里。
// 返回 {platform, at, f, rows}。存成 days/<日期>/metrics/zhihu-<账号>.json → metrics.py ingest zhihu <账号> <文件>
await (async () => {
  const F = ['id', 'created', 'title', 'type', 'views', 'likes', 'comments', 'favorites', 'shares'];
  const rows = [];
  const since = Date.now() / 1000 - 45 * 86400;
  for (let off = 0; off < 100; off += 20) {
    const r = await fetch(`/api/v4/creators/creations/v2/all?start=0&end=0&limit=20&offset=${off}`, { credentials: 'include' });
    const j = await r.json();
    const list = j.data || [];
    if (!list.length) break;
    let old = false;
    for (const x of list) {
      const d = x.data || {}, rc = x.reaction || {};
      const ts = +d.created_time || 0;
      if (ts < since) { old = true; continue; }
      const title = (d.title || d.excerpt || '').replace(/\s+/g, ' ').slice(0, 40);
      rows.push([`${x.type}-${d.id}`, ts, title, x.type, +(rc.read_count || rc.play_count || rc.view_count || 0), +(rc.vote_up_count || rc.like_count || 0),
        +(rc.comment_count || 0), +(rc.collect_count || 0), +(rc.repin_count || 0)]);
    }
    if (old || j.paging?.is_end) break;
  }
  return JSON.stringify({ platform: 'zhihu', at: Math.round(Date.now() / 1000), f: F, rows });
})()
