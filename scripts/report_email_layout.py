"""邮件专用 HTML 布局：摘要优先，完整流水留在附件。无远程字体/图片。"""
import html
import re


def parse_tables(text):
    tables, rows = [], []
    for line in text.splitlines() + ['']:
        if line.startswith('|'):
            cells = [v.strip().replace('\\|', '|') for v in re.split(r'(?<!\\)\|', line.strip().strip('|'))]
            if not all(re.fullmatch(r':?-+:?', v) for v in cells):
                rows.append(cells)
        elif rows:
            tables.append(rows)
            rows = []
    return tables


def safe(value):
    value = str(value or '—')
    parts = re.split(r'(https?://[^\s<>]+)', value)
    return ''.join(f'<a href="{html.escape(p, quote=True)}" style="color:#2364bd;text-decoration:underline">查看原帖</a>' if p.startswith(('https://', 'http://')) else html.escape(p) for p in parts)


def data_table(headers, rows, widths=None):
    th = ''.join(f'<th align="left" style="padding:10px 12px;background:#edf2f8;border-bottom:1px solid #d8e1ec;font-size:12px;color:#4b5b70;font-weight:600;{f"width:{widths[i]}%;" if widths else ""}">{safe(h)}</th>' for i,h in enumerate(headers))
    body = ''.join('<tr>' + ''.join(f'<td valign="top" style="padding:12px;border-bottom:1px solid #e5eaf0;background:{"#ffffff" if n%2==0 else "#f8fafc"};font-size:14px;line-height:1.8;overflow-wrap:anywhere;word-break:break-word;">{c}</td>' for c in row) + '</tr>' for n,row in enumerate(rows))
    return f'<table width="100%" cellpadding="0" cellspacing="0" style="width:100%;border:1px solid #e0e6ee;border-radius:8px;border-spacing:0;table-layout:fixed;">{f"<thead><tr>{th}</tr></thead>"}<tbody>{body}</tbody></table>'


def section(title, content, note=''):
    note_html = '<p style="font-size:12px;color:#627389;margin:0 0 12px;line-height:1.8;">' + note + '</p>' if note else ''
    return f'<tr><td class="content" style="padding:0 28px 26px;"><h2 style="font-size:18px;line-height:1.5;margin:0 0 12px;color:#172c49;">{title}</h2>{note_html}{content}</td></tr>'


def build_email(text, day, site_url):
    sections = {}
    for part in re.split(r'^## ', text, flags=re.M)[1:]:
        title, _, content = part.partition('\n')
        sections[title.strip()] = content
    def rows(name):
        ts = parse_tables(sections.get(name, ''))
        return ts[0][1:] if ts else []
    overview = sections.get('一天概况', '')
    matched = re.search(r'平台报成功/网页发表 (\d+) 条，其中核验公开且有链接 (\d+) 条', overview)
    counts = [matched.group(1), matched.group(2)] if matched else ['—','—']
    p = re.search(r'失败/阻断 (\d+) 条，待核实 (\d+) 条', overview)
    counts += [str(int(p.group(1)) + int(p.group(2))) if p else '—']
    interactions = re.search(r'互动合计 (\d+) 次', sections.get('全天互动', ''))
    counts += [interactions.group(1) if interactions else '—']
    stats = ''.join(f'<td class="stat" width="25%" valign="top" style="padding:18px 8px;border-right:1px solid #e2e8f0;text-align:center;"><div style="font-size:30px;line-height:1.3;font-weight:700;color:{"#9a5b13" if i==2 else "#172c49"};">{v}</div><div style="font-size:12px;color:#596b83;padding-top:6px;">{label}</div></td>' for i,(v,label) in enumerate(zip(counts,['台账成功','核验公开','需跟进','互动次数'])))
    url = site_url.rstrip('/') + '/#/reports/' + day if site_url else ''
    link = f'<a href="{html.escape(url,quote=True)}" style="display:inline-block;background:#1e4f86;color:#ffffff;font-size:14px;font-weight:600;text-decoration:none;padding:12px 22px;border-radius:7px;">打开完整报告</a>' if url else ''
    head = f'''<!doctype html><html lang="zh-CN"><head><meta name="viewport" content="width=device-width,initial-scale=1"><meta charset="UTF-8"><style>@media only screen and (max-width:600px){{.content{{padding-left:16px!important;padding-right:16px!important}}.stat{{display:inline-block!important;width:49%!important;box-sizing:border-box!important}}.mail-wrap{{width:100%!important}}}}</style></head><body style="margin:0;padding:0;background:#edf2f7;color:#27364a;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',Arial,sans-serif;">
<div style="display:none;font-size:1px;line-height:1px;color:#edf2f7;max-height:0;overflow:hidden;">{day} 全天运营 · 平台成功{counts[0]}条 · 已核验公开{counts[1]}条 · 需跟进{counts[2]}项</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#edf2f7;"><tr><td align="center" style="padding:24px 10px;">
<table role="presentation" class="mail-wrap" width="720" cellspacing="0" cellpadding="0" style="width:100%;max-width:720px;background:#ffffff;border:1px solid #dbe3ed;border-radius:12px;overflow:hidden;">
<tr><td class="content" style="padding:30px 28px 24px;border-top:5px solid #1e4f86;"><p style="margin:0 0 8px;color:#526782;font-size:13px;">示例作者矩阵 · 每日运营</p><h1 style="font-size:28px;line-height:1.4;color:#172c49;margin:0 0 10px;">全天运营日报</h1><p style="font-size:15px;margin:0;color:#50627b;">{day}<span style="color:#8492a6"> ｜ </span>00:00–24:00 北京时间</p><p style="font-size:13px;color:#63748a;line-height:1.9;margin:14px 0 0;">先看结果，再看需要跟进的事。完整发布、互动和任务流水已放入附件，也可在工作台阅读。</p></td></tr>
<tr><td class="content" style="padding:0 28px 26px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f6fa;border:1px solid #e0e7ef;border-radius:8px;"><tr>{stats}</tr></table><p style="font-size:12px;color:#697b91;line-height:1.8;margin:10px 0 0;">摘要按已接入台账统计；旧流程的历史数据见复盘。核验公开另需平台证据，定时到点仍待核实。</p></td></tr>'''
    content = ''
    historical = sections.get('晚间复盘（保留原文及其统计口径）', '')
    correction = re.search(r'^### 更正[^\n]*\n(.*?)(?=^### |\Z)', historical, re.M | re.S)
    if correction:
        content += section('历史核验更正', '<div style="background:#edf7f1;border-left:3px solid #3a8061;padding:14px;font-size:14px;line-height:1.9;">' + safe(correction.group(1).strip()) + '</div>', '历史记录与旧台账不一致时，以下已记录的核验更正优先；旧台账异常需要回填，不能据此直接重发。')
    problems = rows('异常与待处理')
    if problems:
        content += section('台账待核对', data_table(['内容与状态','原因 / 下一步'], [[f'<b>{safe(r[0])}</b><br><span style="color:#9a5b13">{safe(r[1])}</span>',safe(r[2])] for r in problems if len(r)>=3], [38,62]))
    else:
        content += section('需要跟进', '<p style="background:#edf7f1;padding:14px;color:#286443;border-radius:6px;font-size:14px;">台账没有未解决的发布异常。</p>')
    account_rows=[]
    for r in rows('各账号完成情况'):
        if len(r)>=6:
            account_rows.append([safe(r[0]),f'<b>{safe(r[2])}</b> / {safe(r[1])}',f'待发 {safe(r[3])}<br>失败 {safe(r[4])} · 待核实 {safe(r[5])}'])
    content += section('各账号进度', data_table(['平台 / 账号','成功 / 应发','待处理'],account_rows,[44,22,34]), '应发参照当前排期；历史配额调整以当日手册为准。撤销及已替代记录不计完成。')
    pub = []
    for r in rows('全天发布明细'):
        if len(r)>=5:
            url_cell = safe(r[4]) if r[4]!='待回收' else '<span style="color:#8794a5">链接待回收</span>'
            pub.append([safe(r[0]), f'<b>{safe(r[2])}</b><br><span style="font-size:12px;color:#6c7d91">{safe(r[1])}</span>', f'{safe(r[3])}<br>{url_cell}'])
    content += section('全天发布', data_table(['时间','内容','结果'],pub,[13,60,27]), '保留重试与撤销记录，方便检查实际结果；状态截至生成时间。')
    metrics=rows('作品表现')
    if metrics:
        content += section('作品表现', data_table(['平台 / 作品','累计播放','赞 / 评 / 藏'], [[f'{safe(r[0])}<br><b>{safe(r[1])}</b>',safe(r[2]),' / '.join(safe(v) for v in r[3:6])] for r in metrics[:8] if len(r)>=6],[55,20,25]), '当天结束前采集的累计快照，非当日新增；邮件展示前8条，完整数据在附件。')
    else:
        content += section('作品表现','<p style="font-size:14px;color:#63748a;line-height:1.8;">没有符合统计窗口的快照。缺失数据保留为空，不计作零。</p>')
    fans=rows('粉丝变化')
    content += section('粉丝变化',data_table(['账号','当日粉丝','较前一日'], [[f'{safe(r[0])}<br>{safe(r[1])}',safe(r[2]),safe(r[3])] for r in fans if len(r)>=4],[45,22,33]), '比较两个自然日各自最后一次采集；没有可比记录就标缺失。')
    eng=rows('全天互动')
    run_counts={}
    for r in rows('任务运行与热点'):
        if len(r)>=4:
            c=run_counts.setdefault(r[0],[0,0]); c[0]+=1; c[1]+=int(r[2] not in ('无收工记录','—',''))
    content += section('互动与任务',(data_table(['平台','动作','次数'],[[safe(v) for v in r] for r in eng if len(r)==3]) if eng else '<p style="font-size:14px;color:#63748a">当日没有互动采集记录，缺失不代表0。</p>') + '<div style="height:14px"></div>' + (data_table(['任务','运行次数','有收工记录'],[[safe(k),str(v[0]),str(v[1])] for k,v in run_counts.items()]) if run_counts else '<p style="font-size:14px;color:#63748a">当日没有任务运行日志。</p>'),'详细互动文字、热点决策与运行流水在完整报告中。')
    review = sections.get('晚间复盘（保留原文及其统计口径）','')
    m = re.search(r'^### 复盘与次日调整\s*\n(.*?)(?=^### |\Z)',review,re.M|re.S)
    if m:
        review_text = m.group(1)
        if correction:
            review_text = re.sub(r'^#### 今日完成情况.*?(?=^#### |\Z)', '', review_text, flags=re.M | re.S)
        review_lines = review_text.splitlines()
        parts, table_lines = [], []
        def flush_table():
            if table_lines:
                parsed = parse_tables('\n'.join(table_lines))
                if parsed:
                    t = parsed[0]
                    parts.append(data_table(t[0], [[safe(v) for v in row] for row in t[1:]]))
                table_lines.clear()
        for line in review_lines + ['']:
            if line.startswith('|'):
                table_lines.append(line)
                continue
            flush_table()
            line = line.strip()
            if not line:
                continue
            bold = line.startswith('#')
            value = safe(line.lstrip('# ').strip() if bold else line)
            value = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', value)
            parts.append('<p style="margin:12px 0;line-height:1.9;">' + ('<b>' + value + '</b>' if bold else value) + '</p>')
        body = ''.join(parts)
        content += section('复盘与次日调整','<div style="font-size:14px;line-height:1.9;color:#364a63">'+body+'</div>', '保留晚间复盘当时的统计口径；后续更正与当前状态以完整报告明细为准。')
    footer = f'''<tr><td class="content" style="padding:4px 28px 28px;">{link}<p style="font-size:12px;color:#728298;line-height:1.9;margin:16px 0 0;">完整 Markdown 报告见附件，包含全部流水与原始复盘。<br>未采集的收入、成本和私信不推测；平台公开状态以回读为准。</p></td></tr><tr><td class="content" style="background:#f5f7fa;padding:16px 28px;color:#738198;font-size:12px;line-height:1.8;">每日 09:00 发送前一日完整报告 · 北京时间<br>示例作者矩阵运营工作台</td></tr></table></td></tr></table></body></html>'''
    return head + content + footer
