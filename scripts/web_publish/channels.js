// 视频号网页发表（10-16 起视频号默认走这里，不走蚁小二：视频号网页端只能一处登录，内置浏览器登着视频号助手，蚁小二那边会被挤成「登录失效」）。
// 用法：在已登录的 channels.weixin.qq.com/platform/post/create 标签页里，用 javascript_tool 执行本文件；先把下面 CFG 改成这条作品的参数。
//   视频和封面先用 `.venv/bin/python scripts/oss_url.py <文件>` 传到 OSS，拿 https://media.example.com/example.png 地址填进来。
// 关键坑：
//   1. 定时时间不能靠点时间选择器（点完输入框显示变了，内部值还是默认 08:00）。要设组件的 time 再调 handleTimeChange()，见第 4 步。
//   2. 描述用 execCommand('insertText')，#话题 后面带空格才会变成话题标签。
//   3. 浏览器面板隐藏时弹窗关不掉（动画不跑），手动派发 animationend。
//   4. 封面（10-16 起按 封面规范.md 上传 <id>-cover-34.jpg，不用第 0 帧）：先点 .cover-preview-wrap .edit-btn 打开「编辑封面」，
//      弹窗开着时再往弹窗里的图片 input 塞文件，然后点「上传封面」那格（.single-cover-uploader-wrap .finish-wrap）选中，最后「确认」。
//      弹窗没打开就塞文件不会生效。确认后要等几秒，外面封面预览的地址带 bizid=1023 才是上传图（视频帧也是 finder.video.qq.com，不能拿域名判断）。
//   5. 「修改并重新发表」（改已排定时的作品）会把自定义封面和视频标注都重置成默认：10-16 09:00 那条就是改时间后发成了视频第 1 帧。
//      改定时作品时一定重跑封面这一步，发表前看外面预览是上传图。浏览器面板隐藏时先 resize_window 1280x900，不然弹窗打不开。
// 返回 {ok, effectiveTime, steps}；ok=true 后会跳到作品列表，列表里应显示「将于 … 发表」。
const CFG = {
  video: 'https://media.example.com/example.png',
  cover: 'https://media.example.com/example.png',   // 3:4 封面（ai_cover 出的 -cover-34.jpg）；null = 用第 0 帧
  desc: '描述正文（不含话题）',
  topics: ['AI工作台', 'AI智能体'],
  shortTitle: '短标题≤16字',
  at: '2026-10-16T21:30:00+08:00',   // 定时发表时间；null = 立即发表
  aiLabel: false,                      // 10-16 用户：所有平台不勾 AI 声明（「含AI生成内容」不标）
  submit: true,                        // false = 只填表不点发表（演练用）
};
await (async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const steps = [];
  const fw = [...document.querySelectorAll('iframe')].map(f => f.contentWindow).find(w => { try { return w.location.pathname.includes('/micro/content'); } catch (e) { return false; } });
  if (!fw || !fw.location.pathname.includes('/post/create')) return JSON.stringify({ ok: false, error: '先打开 channels.weixin.qq.com/platform/post/create（未登录就让用户扫码）' });
  const d = fw.document;
  const leaf = (t, root = d) => [...root.querySelectorAll('*')].find(e => e.children.length === 0 && e.textContent.trim() === t && e.getBoundingClientRect().width > 0);
  // 1. 视频
  const blob = await (await fw.fetch(CFG.video, { referrerPolicy: 'no-referrer' })).blob();
  if (blob.size < 100000) return JSON.stringify({ ok: false, error: `视频下载异常（${blob.size} 字节），检查 OSS 地址` });
  const vin = d.querySelector('input[type=file][accept*=video]');
  const dt = new fw.DataTransfer(); dt.items.add(new fw.File([blob], CFG.video.split('/').pop(), { type: 'video/mp4', lastModified: Date.now() }));
  vin.files = dt.files; vin.dispatchEvent(new fw.Event('change', { bubbles: true }));
  steps.push(`视频 ${(blob.size / 1e6).toFixed(1)}MB`);
  await sleep(6000);
  // 1.5 封面
  if (CFG.cover) {
    let eb = null;
    for (let i = 0; i < 20 && !eb; i++) { eb = d.querySelector('.cover-preview-wrap .edit-btn'); if (!eb) await sleep(1000); }
    if (!eb) return JSON.stringify({ ok: false, error: '找不到封面「编辑」按钮（视频还没处理完？）', steps });
    eb.click(); await sleep(1500);
    d.querySelectorAll('*').forEach(x => x.dispatchEvent(new fw.AnimationEvent('animationend', { bubbles: true })));
    const dlg = [...d.querySelectorAll('.weui-desktop-dialog')].find(x => /编辑封面/.test(x.textContent));
    const cb = await (await fw.fetch(CFG.cover, { referrerPolicy: 'no-referrer' })).blob();
    const cdt = new fw.DataTransfer(); cdt.items.add(new fw.File([cb], 'cover.jpg', { type: 'image/jpeg', lastModified: Date.now() }));
    const iin = dlg.querySelector('input[type=file][accept*=image]');
    const before = (d.querySelector('.cover-preview-wrap img') || {}).src || '';
    iin.files = cdt.files; iin.dispatchEvent(new fw.Event('change', { bubbles: true }));
    let fin = null;
    for (let i = 0; i < 12 && !fin; i++) { await sleep(1500); fin = dlg.querySelector('.single-cover-uploader-wrap .finish-wrap'); }
    if (!fin) return JSON.stringify({ ok: false, error: '封面上传没完成', steps });
    // 选中「上传封面」那格；弹窗组件 EditCoverDialog 的 useCustomCover 变 true 才算选中（10-16 发现不核对会静默用回视频帧）
    const ecd = (() => { let v = dlg.querySelector('.single-cover-uploader-wrap').__vue__; while (v && v.$options.name !== 'EditCoverDialog') v = v.$parent; return v; })();
    for (let i = 0; i < 3; i++) {
      ['mousedown', 'mouseup', 'click'].forEach(ev => fin.dispatchEvent(new fw.MouseEvent(ev, { bubbles: true })));
      await sleep(1500);
      if (!ecd || ecd.useCustomCover) break;
    }
    if (ecd && !ecd.useCustomCover) return JSON.stringify({ ok: false, error: '弹窗里没选中上传的封面（useCustomCover=false）', steps });
    [...dlg.querySelectorAll('button')].find(b => b.textContent.trim() === '确认').click();
    // 确认后视频号要把封面再传一遍，外面的预览要过几秒才换成上传图（地址带 bizid=1023）；视频帧的地址没有这个参数
    let okc = false;
    for (let i = 0; i < 20 && !okc; i++) {
      await sleep(1500);
      d.querySelectorAll('*').forEach(x => x.dispatchEvent(new fw.AnimationEvent('animationend', { bubbles: true })));
      const now = (d.querySelector('.cover-preview-wrap img') || {}).src || '';
      okc = /bizid=1023/.test(now) && now !== before;
    }
    if (!okc) return JSON.stringify({ ok: false, error: '封面没换上（30 秒内外面预览没变成上传图），别提交，重跑封面这一步', steps });
    steps.push('封面 已换成 3:4 上传图');
  }
  // 2. 描述 + 话题
  const ed = d.querySelector('[contenteditable]');
  ed.focus();
  d.execCommand('insertText', false, CFG.desc.trim() + ' ');
  for (const t of CFG.topics || []) { d.execCommand('insertText', false, `#${t} `); await sleep(600); }
  ed.blur();
  steps.push(`描述 ${ed.innerText.length} 字，话题 ${ed.querySelectorAll('.topic').length} 个`);
  // 3. 短标题
  const st = d.querySelector('input[placeholder*="短标题"]');
  const setter = Object.getOwnPropertyDescriptor(fw.HTMLInputElement.prototype, 'value').set;
  st.focus(); setter.call(st, CFG.shortTitle.slice(0, 16)); st.dispatchEvent(new fw.Event('input', { bubbles: true })); st.blur();
  // 4. 定时
  let effectiveTime = null;
  if (CFG.at) {
    const lab = [...d.querySelectorAll('label,span,div')].find(e => e.children.length <= 2 && e.textContent.trim() === '定时' && e.getBoundingClientRect().width > 0);
    (lab.closest('label') || lab).click();
    await sleep(800);
    const main = d.querySelector('input[placeholder="请选择发表时间"]');
    let el = main, vm = null; while (el && !vm) { vm = el.__vue__ || null; el = el.parentElement; }
    const host = vm.$parent.$parent;
    host.time = new Date(CFG.at).getTime(); host.handleTimeChange();
    await sleep(500);
    effectiveTime = (host.postStore || host.$props.postStore).effectiveTime;
    if (Math.abs(effectiveTime * 1000 - new Date(CFG.at).getTime()) > 60000) return JSON.stringify({ ok: false, error: `定时没设上：effectiveTime=${effectiveTime}`, steps });
    steps.push(`定时 ${main.value}`);
  }
  // 5. AI 标注
  if (CFG.aiLabel) {
    const t = leaf('选择视频标注'); t && t.click(); await sleep(1000);
    const o = leaf('含AI生成内容'); o && o.click(); await sleep(800);
    steps.push(leaf('含AI生成内容') ? '标注 含AI生成内容' : '标注失败');
  }
  // 6. 发表（等上传完成：completepartuploaddfs 出现）
  for (let i = 0; i < 60; i++) {
    if (fw.performance.getEntriesByType('resource').some(e => /completepartuploaddfs/.test(e.name))) break;
    await sleep(2000);
  }
  if (!CFG.submit) return JSON.stringify({ ok: true, dryRun: true, effectiveTime, steps });
  const btn = [...d.querySelectorAll('button')].find(b => b.textContent.trim() === '发表' && b.getBoundingClientRect().width > 0);
  btn.click();
  await sleep(4000);
  return JSON.stringify({ ok: fw.location.pathname.includes('/post/list'), effectiveTime, steps, after: fw.document.body.innerText.slice(0, 200) });
})()
