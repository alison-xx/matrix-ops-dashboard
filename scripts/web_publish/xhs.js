// 小红书网页发布图文（10-16 蚁小二快代理入口挂掉时的兜底；用户授权「实在没代理就用本机 IP 提交」）。
// 用法：内置浏览器打开 https://creator.xiaohongshu.com/publish/publish?source=official&from=tab_switch&target=image
//      （已登录「示例聊AI」），先 resize_window 1280x900（面板太小时底部「发布」按钮不渲染），改好 CFG 后用 javascript_tool 执行本文件。
//      图片先在 OSS（post.uploads.json 里有地址），没有就 `.venv/bin/python scripts/oss_url.py <文件>`。
// 坑（10-16 实测）：
//   1. 话题要输入「#话题名」后从联想列表（div.item）里点选，才会变成真正的话题；直接写 #xx 只是文字。
//   2. 内容类型声明是 d-select，选项在隐藏面板里（高度为 0），直接对 .d-option 派发 mousedown/mouseup/click。
//   3. 定时：打开「定时发布」开关后，用 execCommand('insertText') 改 .date-picker-container input，回车再失焦；改完核对值没回弹。
//   4. 底部提交按钮 DOM 查不到文字时，用截图坐标点（1280x900 视口下约在 (436,534)）；提交后到「笔记管理」核对显示「定时发布 YYYY-MM-DD HH:MM」。
//   5. 有些话题是官方活动话题（如 #我这行的AI路），选上会自动「关联活动」；不想关联就对 .activity-action「取消关联」直接 .click()。
//      别在活动卡片上用坐标点，会弹出活动详情遮住提交按钮。
// 返回 {ok, steps}；submit=false 只填表不提交。提交后要 `ops.py web <id> xhs HH:MM <post.json> "网页兜底…"` 登记。
const CFG = {
  images: ['https://media.example.com/example.png'],
  title: '标题≤20字',
  desc: '正文，空行分段\n\n结尾问题？\n\n#话题1 #话题2',
  aiDeclare: false,          // 10-16 用户：所有平台不勾 AI 声明（「笔记含AI合成内容」不选）
  at: '2026-10-16 12:20',    // null = 立即发布
  submit: false,
};
await (async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const steps = [];
  const fire = (el, evs = ['mousedown', 'mouseup', 'click']) => evs.forEach(ev => el.dispatchEvent(new MouseEvent(ev, { bubbles: true })));
  // 1. 图片
  const dt = new DataTransfer();
  for (const [i, u] of CFG.images.entries()) {
    const b = await (await fetch(u, { referrerPolicy: 'no-referrer' })).blob();
    if (b.size < 10000) return JSON.stringify({ ok: false, error: `图片下载异常 ${u}` });
    dt.items.add(new File([b], `${i + 1}.jpg`, { type: b.type || 'image/jpeg', lastModified: Date.now() }));
  }
  const inp = document.querySelector('input[type=file]');
  inp.files = dt.files; inp.dispatchEvent(new Event('change', { bubbles: true }));
  await sleep(4000 + CFG.images.length * 800);
  steps.push(`图片 ${dt.files.length}`);
  // 2. 标题
  const t = document.querySelector('input.d-text[placeholder*="标题"]');
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  t.focus(); setter.call(t, CFG.title.slice(0, 20)); t.dispatchEvent(new Event('input', { bubbles: true })); t.dispatchEvent(new Event('change', { bubbles: true })); t.blur();
  // 3. 正文（话题单独处理）
  const body = CFG.desc.replace(/\n*(#\S+\s*)+$/, '').trim();
  const topics = (CFG.desc.match(/#(\S+)/g) || []).map(x => x.slice(1));
  const ed = document.querySelector('.tiptap.ProseMirror'); ed.focus();
  const lines = body.split('\n');
  for (let i = 0; i < lines.length; i++) { if (lines[i]) document.execCommand('insertText', false, lines[i]); if (i < lines.length - 1) document.execCommand('insertParagraph'); }
  steps.push(`正文 ${ed.innerText.length} 字`);
  // 4. 话题
  const pick = async (tp) => {
    for (let k = 0; k < 10; k++) {
      const items = [...document.querySelectorAll('div.item')].filter(e => e.getBoundingClientRect().height > 0 && e.innerText.trim().startsWith('#'));
      if (items.length) { const hit = items.find(e => e.innerText.split('\n')[0].trim() === '#' + tp) || items[0]; const name = hit.innerText.split('\n')[0]; fire(hit); await sleep(500); return name; }
      await sleep(300);
    }
    return null;
  };
  if (topics.length) { ed.focus(); document.execCommand('insertParagraph'); }
  const got = [];
  for (const [i, tp] of topics.entries()) { ed.focus(); document.execCommand('insertText', false, (i ? ' #' : '#') + tp); await sleep(1200); got.push(await pick(tp)); }
  steps.push(`话题 ${got.join(' ')}`);
  // 5. AI 声明
  if (CFG.aiDeclare) {
    const w = [...document.querySelectorAll('.d-select-wrapper')].find(x => /内容类型声明/.test(x.textContent));
    if (w) { fire(w.querySelector('.d-select')); await sleep(1000); }
    const opt = [...document.querySelectorAll('.d-option')].find(e => e.textContent.trim() === '笔记含AI合成内容');
    if (opt) { fire(opt); await sleep(600); }
    steps.push('声明 ' + ([...document.querySelectorAll('.d-select-wrapper')].map(x => x.textContent.trim()).find(x => /AI合成/.test(x)) || '失败'));
  }
  // 6. 定时
  if (CFG.at) {
    const lab = [...document.querySelectorAll('span.has-tips')].find(e => e.textContent.trim() === '定时发布');
    const sw = lab.closest('.custom-switch-card').querySelector('.d-switch');
    if (!document.querySelector('.date-picker-container input')) { sw.click(); await sleep(1200); }
    const di = document.querySelector('.date-picker-container input');
    di.focus(); di.select(); document.execCommand('insertText', false, CFG.at); await sleep(300);
    di.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }));
    await sleep(300); di.blur(); di.dispatchEvent(new Event('change', { bubbles: true })); await sleep(800);
    if (di.value !== CFG.at) return JSON.stringify({ ok: false, error: `定时没设上：${di.value}`, steps });
    steps.push(`定时 ${di.value}`);
  }
  if (!CFG.submit) return JSON.stringify({ ok: true, dryRun: true, steps });
  return JSON.stringify({ ok: true, steps, next: '截图找到底部「定时发布/发布」按钮坐标点击，然后去笔记管理核对' });
})()
