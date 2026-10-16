// 快手网页发布视频（10-16 新增）。默认走网页（能设封面、定时、作者声明），接口留作网页登录失效时的兜底（build_payload slot kuaishou）。
// 10-16 用户：「以后都不勾选 AI 声明，其他平台也一样」→ aiDeclare 默认 false，不要改回 true。
// 用法：内置浏览器打开 https://cp.kuaishou.com/article/publish/video（已登录「示例聊AI」；没登录就生成登录码，用 scripts/qr_mail.py 发邮件请用户扫），
//      建议先 resize_window 1280x900，改好 CFG 后用 javascript_tool 执行本文件；提交后 `ops.py web <id> kuaishou HH:MM <post.json> "网页发布"` 登记。
// 10-16 实测要点：
//   1. 视频 input 的 accept 含 video/*，DataTransfer 塞文件 + change 事件即可；上传后表单出来要 10 秒左右。
//   2. 描述框是 contenteditable（class 含 _description_），execCommand('insertText')；话题直接写「#AI工具」文字即可（不用点联想）。
//   3. 封面：点 _cover-full-editor 打开「封面截取/上传封面」弹窗 → 点「上传封面」→ 往图片 input 塞 3:4 封面 → 出现「清空上传」→ 选「3:4」→「确认」。
//   4. 作者声明：ant-select（占位「为作品添加补充说明」），对 .ant-select-item-option「内容为AI生成」派发 mousedown/mouseup/click。
//   5. 定时：点 value=2 的「定时发布」单选 → 点只读的 ant-picker 输入框 → 面板里点 td[title=日期]、三列时/分/秒 li → 「确定」，读回输入框核对。
//   6. 平台提示粉丝活跃 20:00–21:00（10-16），主时段排 20:30。
const CFG = {
  video: 'https://media.example.com/example.png',
  cover: 'https://media.example.com/example.png',   // 3:4 封面（和抖音同一套）
  desc: '第一句给结论或数字。第二句补一句。 #AI工具 #AI教程 #办公技巧 #人工智能',
  aiDeclare: false,          // 10-16 用户：所有平台不勾 AI 声明
  at: '2026-10-16 20:30:00',   // null = 立即发布
  submit: false,
};
await (async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const fire = el => ['mousedown', 'mouseup', 'click'].forEach(ev => el.dispatchEvent(new MouseEvent(ev, { bubbles: true })));
  const leaf = t => [...document.querySelectorAll('*')].find(e => e.children.length === 0 && e.textContent.trim() === t);
  const steps = [];
  // 1. 视频
  const vb = await (await fetch(CFG.video, { referrerPolicy: 'no-referrer' })).blob();
  if (vb.size < 100000) return JSON.stringify({ ok: false, error: `视频下载异常 ${vb.size}` });
  const vin = [...document.querySelectorAll('input[type=file]')].find(i => /video/.test(i.accept || ''));
  if (!vin) return JSON.stringify({ ok: false, error: '找不到视频上传框（没登录或不在发布页）' });
  const dt = new DataTransfer(); dt.items.add(new File([vb], 'video.mp4', { type: 'video/mp4', lastModified: Date.now() }));
  vin.files = dt.files; vin.dispatchEvent(new Event('change', { bubbles: true }));
  let ed = null;
  for (let i = 0; i < 30 && !ed; i++) { await sleep(1000); ed = document.querySelector('[class*=_description_]'); }
  if (!ed) return JSON.stringify({ ok: false, error: '上传后表单没出来' });
  steps.push(`视频 ${(vb.size / 1e6).toFixed(1)}MB`);
  // 2. 描述
  ed.focus(); document.execCommand('insertText', false, CFG.desc.trim()); await sleep(500);
  steps.push(`描述 ${ed.innerText.length} 字`);
  // 3. 封面
  if (CFG.cover) {
    const opener = [...document.querySelectorAll('div')].find(e => /_cover-full-editor/.test(e.className));
    const coverSrc = () => { const i = opener.querySelector('img'); const bg = [...opener.querySelectorAll('*')].map(e => getComputedStyle(e).backgroundImage).find(b => b && b.startsWith('url(')); return (i && i.src) || bg || ''; };
    const before = coverSrc();
    opener.click(); await sleep(1500);
    const modal = [...document.querySelectorAll('.ant-modal')].find(m => /封面截取/.test(m.textContent));
    [...modal.querySelectorAll('*')].find(e => e.children.length === 0 && e.textContent.trim() === '上传封面').click(); await sleep(1000);
    const cb = await (await fetch(CFG.cover, { referrerPolicy: 'no-referrer' })).blob();
    const ins = [...document.querySelectorAll('input[type=file]')].filter(i => /image/.test(i.accept || ''));
    const cdt = new DataTransfer(); cdt.items.add(new File([cb], 'cover.jpg', { type: 'image/jpeg', lastModified: Date.now() }));
    const ci = ins[ins.length - 1]; ci.files = cdt.files; ci.dispatchEvent(new Event('change', { bubbles: true }));
    await sleep(3500);
    if (!/清空上传/.test(modal.textContent)) return JSON.stringify({ ok: false, error: '封面没传上', steps });
    const r34 = [...modal.querySelectorAll('*')].find(e => e.children.length === 0 && e.textContent.trim() === '3:4');
    (r34.closest('label,button,div') || r34).click(); await sleep(1000);
    [...modal.querySelectorAll('button')].find(b => b.textContent.trim() === '确认').click();
    // 10-16：视频号同类步骤出过「点了确认、实际还是视频帧」，这里等外面的封面预览真的换掉才算数
    let changed = false;
    for (let i = 0; i < 12 && !changed; i++) { await sleep(1500); const now = coverSrc(); changed = !!now && now !== before; }
    if (!changed && before) return JSON.stringify({ ok: false, error: '封面没换上（外面预览没变），别提交，重跑封面这一步', steps });
    steps.push(changed ? '封面 3:4 上传图（已核对预览换了）' : '封面 3:4 上传图（页面上找不到封面预览，发后到作品管理核对封面）');
  }
  // 4. AI 声明
  if (CFG.aiDeclare) {
    const ph = leaf('为作品添加补充说明');
    if (ph) { fire(ph.closest('.ant-select') || ph); await sleep(1000); }
    const opt = [...document.querySelectorAll('.ant-select-item-option')].find(e => e.textContent.trim() === '内容为AI生成');
    if (opt) { fire(opt); await sleep(600); }
    const got = [...document.querySelectorAll('.ant-select-selection-item')].map(e => e.textContent.trim()).find(t => /AI生成/.test(t));
    if (!got) return JSON.stringify({ ok: false, error: 'AI 声明没选上', steps });
    steps.push('声明 内容为AI生成');
  }
  // 5. 定时
  if (CFG.at) {
    const r = [...document.querySelectorAll('input[type=radio]')].find(x => x.value === '2' && /定时发布/.test((x.closest('label') || x.parentElement).textContent));
    (r.closest('label') || r).click(); await sleep(1000);
    const inp = document.querySelector('.ant-picker input');
    fire(inp); inp.focus(); await sleep(1000);
    const panel = document.querySelector('.ant-picker-dropdown:not(.ant-picker-dropdown-hidden)') || document.querySelector('.ant-picker-dropdown');
    const [d, t] = CFG.at.split(' '); const [hh, mm, ss] = t.split(':');
    const day = panel.querySelector(`td[title="${d}"]`); if (day) fire(day.querySelector('.ant-picker-cell-inner') || day); await sleep(300);
    const cols = [...panel.querySelectorAll('.ant-picker-time-panel-column')];
    const pick = (col, v) => { const li = col && [...col.querySelectorAll('li')].find(l => l.textContent.trim() === v); if (li) fire(li.querySelector('.ant-picker-time-panel-cell-inner') || li); };
    pick(cols[0], hh); pick(cols[1], mm); pick(cols[2], ss || '00'); await sleep(400);
    const ok = [...panel.querySelectorAll('button')].find(b => /确\s*定|OK/.test(b.textContent)); if (ok) fire(ok);
    await sleep(800);
    if (inp.value !== `${d} ${hh}:${mm}:${ss || '00'}`) return JSON.stringify({ ok: false, error: `定时没设上：${inp.value}`, steps });
    steps.push(`定时 ${inp.value}`);
  }
  if (!CFG.submit) return JSON.stringify({ ok: true, dryRun: true, steps });
  const pub = [...document.querySelectorAll('button, div')].find(b => b.children.length <= 1 && b.textContent.trim() === '发布' && b.getBoundingClientRect().width > 0);
  pub.click(); await sleep(4000);
  return JSON.stringify({ ok: true, steps, after: location.href, next: '去 cp.kuaishou.com 内容管理核对「定时发布」状态' });
})()
