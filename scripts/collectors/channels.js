// 视频号助手作品数据（在已登录 channels.weixin.qq.com/platform/post/list 的标签页里用 javascript_tool 执行）。
// 列表在同源 iframe（/micro/content）里，直接读卡片：眼睛=播放、心=喜欢、评论、分享=转发、大拇指=推荐。
// 返回 {platform, at, f, rows}；视频号卡片上没有作品 id，用「发布时间+描述前 20 字」做 id。
await (async () => {
  const fw = [...document.querySelectorAll('iframe')].map(f => f.contentWindow).find(w => { try { return w.location.pathname.includes('/micro/content'); } catch (e) { return false; } });
  if (!fw) return JSON.stringify({ error: '先打开 channels.weixin.qq.com/platform/post/list（未登录就扫码）' });
  const d = fw.document;
  const F = ['id', 'created', 'title', 'views', 'favorites', 'comments', 'shares', 'likes'];
  const rows = [];
  for (const pd of d.querySelectorAll('.post-data')) {
    const card = pd.closest('.post-feed-item') || pd.parentElement.parentElement.parentElement;
    const txt = card.innerText;
    const m = txt.match(/(\d{4})年(\d{1,2})月(\d{1,2})日\s+(\d{1,2}):(\d{2})/);
    const ts = m ? Math.round(new Date(`${m[1]}-${m[2].padStart(2, '0')}-${m[3].padStart(2, '0')}T${m[4].padStart(2, '0')}:${m[5]}:00+08:00`).getTime() / 1000) : 0;
    const title = txt.split('\n').map(s => s.trim()).find(s => s.length > 6 && !/^\d{4}年/.test(s)) || '';
    const nums = [...pd.querySelectorAll('.count')].map(e => +(e.textContent.trim().replace(/[^\d.]/g, '')) || 0);
    if (nums.length < 5 || ts < Date.now() / 1000 - 45 * 86400) continue;
    rows.push([`${ts}-${title.slice(0, 20)}`, ts, title.slice(0, 40), nums[0], nums[1], nums[2], nums[3], nums[4]]);
  }
  return JSON.stringify({ platform: 'channels', at: Math.round(Date.now() / 1000), f: F, rows });
})()
