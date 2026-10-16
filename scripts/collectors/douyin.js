// 抖音创作者中心作品数据（在已登录 creator.douyin.com 的标签页里用 javascript_tool 执行，返回紧凑 JSON：{f:[字段], rows:[[...]]}）
// 不含任何链接/令牌；跳过 [dryrun] 测试稿和 45 天前的作品。
// 用法：执行 → 把返回的字符串原样存成 days/<日期>/metrics/douyin-<账号>.json → .venv/bin/python scripts/metrics.py ingest douyin <账号> <文件>
await (async () => {
  const F = ['id', 'created', 'title', 'duration', 'views', 'likes', 'comments', 'favorites', 'shares', 'follows', 'homepage_visits',
             'completion', 'completion_5s', 'bounce_2s', 'avg_view_sec', 'avg_view_ratio', 'cover_show'];
  const rows = [];
  const since = Date.now() / 1000 - 45 * 86400;
  let cursor = 0;
  for (let page = 0; page < 3; page++) {
    const r = await fetch(`/janus/douyin/creator/pc/work_list?status=0&count=20&max_cursor=${cursor}&scene=star_atlas&device_platform=android&aid=1128`, { credentials: 'include' });
    const j = await r.json();
    if (j.status_code !== 0) break;
    const aw = j.aweme_list || [];
    for (const it of j.items || []) {
      if (it.create_time < since) continue;
      const desc = (it.description || '').split('\n')[0];
      if (desc.startsWith('[dryrun]')) continue;
      const a = aw.find(x => String(x.create_time) === String(it.create_time)) || {};
      const m = it.metrics || {}, st = a.statistics || {};
      const n = v => +(v || 0);
      rows.push([String(a.aweme_id || ''), it.create_time, desc.slice(0, 40), Math.round(((it.video_info || {}).duration || 0) / 1000),
        n(m.view_count) || n(st.play_count), n(m.like_count) || n(st.digg_count), n(m.comment_count) || n(st.comment_count),
        n(m.favorite_count) || n(st.collect_count), n(m.share_count) || n(st.share_count), n(m.subscribe_count), n(m.homepage_visit_count),
        +n(m.completion_rate).toFixed(3), +n(m.completion_rate_5s).toFixed(3), +n(m.bounce_rate_2s).toFixed(3),
        +n(m.avg_view_second).toFixed(1), +n(m.avg_view_proportion).toFixed(3), n(m.cover_show)]);
    }
    if (!j.has_more) break;
    cursor = j.max_cursor;
  }
  return JSON.stringify({ platform: 'douyin', at: Math.round(Date.now() / 1000), f: F, rows });
})()
