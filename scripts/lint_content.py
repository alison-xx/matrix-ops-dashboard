#!/usr/bin/env python3
"""发布前内容体检：从 payload（+正文文件、同目录口播 spec）抽出标题/正文/口播，按平台规则查
营销词、AI 腔、破折号、emoji、话题数、markdown 残留、占位符、篇幅、结尾互动。

error 拦截入台账（ops.py add 会调用）；warn 只提示，由批次任务决定改不改。
确需保留的词（如引用官方原话里的「助力」）：在同目录 review.md 里写一行 `lint-allow: 助力,里程碑`。
另跑 human-writing skill 的 check_prose.py（句长变化、连词密度、翻案句变形等），只出 warn，前缀「活人感·」；没装就跳过。
用法: .venv/bin/python scripts/lint_content.py <payload.json> [--content-file x.md]
"""
import collections, html, json, pathlib, re, sys

HYPE = ['震惊', '炸裂', '王炸', '天花板', '保姆级', '全网都在', '建议收藏', 'yyds', 'YYDS', '封神', '杀疯', '吊打', '史诗级',
        '绝绝子', '家人们谁懂', '宝子们', '重磅', '速看', '必看', '逆天', '颠覆', '一键搞定', '躺赚', '月入过万', '暴富']
# 明确的 AI 腔：出现即拦截
AI_ERR = [r'在当今', r'随着.{0,14}(飞速|快速|迅猛|蓬勃)发展', r'在这个.{0,10}时代', r'综上所述', r'总而言之', r'总的来说',
          r'让我们拭目以待', r'未来可期', r'未来已来', r'拥抱变化', r'希望(以上内容)?对你有(所)?帮助', r'好问题', r'作为一(个|名|款)?\s*AI',
          r'以下是', r'值得注意的是', r'需要指出的是', r'毋庸置疑', r'不难发现', r'众所周知', r'赋能', r'抓手', r'闭环', r'底层逻辑',
          r'降本增效', r'深度融合', r'全方位', r'里程碑', r'革命性', r'划时代', r'不禁感叹', r'令人震撼', r'稳稳接住']
# 可能是 AI 腔：提示
AI_WARN = [r'不是[^，。！？\n]{1,20}而是', r'与其说.{1,20}不如说', r'你以为.{1,20}其实', r'说白了', r'说穿了', r'掰开了?揉碎了?',
           r'带大家', r'教大家', r'这说明什么', r'为什么？因为', r'不仅仅?是.{1,20}更是', r'有利有弊', r'因人而异', r'机遇.{0,4}挑战',
           r'至关重要', r'不可或缺', r'极大地', r'显著(提升|提高|改善)', r'研究表明', r'据统计', r'业内人士', r'助力', r'神器',
           r'一起来看看', r'话不多说', r'干货', r'事实上', r'不得不说', r'更重要的是', r'关键在于', r'问题在于']
PLACEHOLDER = [r'TODO', r'XXX', r'待补', r'占位', r'实测填', r'【X】', r'【N】', r'（此处', r'\[插图\]', r'<[a-zA-Z_]+>', r'＜.+?＞']
EMOJI_RE = re.compile('[\U0001F300-\U0001FAFF☀-➿\U0001F000-\U0001F2FF]')
TAG_RE = re.compile(r'#([^#\s]{1,30})#?')

# 平台规则：title_max 标题字数上限；tags (min,max)；emoji 正文上限；body (min,max) 正文字数建议；ask 结尾要不要提问
RULES = {
    '抖音':       {'title_max': 30, 'tags': (2, 6), 'emoji': 2, 'body': (20, 300), 'ask': True},
    '视频号':     {'title_max': 30, 'tags': (1, 4), 'emoji': 1, 'body': (20, 300), 'ask': True},
    '哔哩哔哩-Open': {'title_max': 40, 'tags': (3, 10), 'emoji': 1, 'body': (30, 600), 'ask': True},
    '小红书':     {'title_max': 20, 'tags': (3, 6), 'emoji': 5, 'body': (150, 1000), 'ask': True},
    '新浪微博':   {'title_max': 80, 'tags': (1, 2), 'emoji': 2, 'body': (50, 450), 'ask': True},
    '知乎':       {'title_max': 50, 'tags': (0, 0), 'emoji': 0, 'body': (500, 3500), 'ask': False},
    '微信公众号': {'title_max': 64, 'tags': (0, 0), 'emoji': 3, 'body': (900, 5000), 'ask': False},
}


def strip_html(s):
    s = re.sub(r'<(br|/p|/section|/h\d|/li)[^>]*>', '\n', s or '')
    return html.unescape(re.sub(r'<[^>]+>', '', s))


def strip_md(s):
    s = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', s)
    s = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', s)
    return re.sub(r'[#>*`|-]{1,}', ' ', s)


def extract(o, content_file=None):
    plat = o['platforms'][0]
    ptype = o.get('publishType')
    pa = o['publishArgs']
    if plat == '微信公众号' and ptype != 'imageText':   # 公众号贴图走下面的 accountForms 分支（描述字段叫 desc）
        art = pa['platformForms'][plat]['articles'][0]
        return plat, ptype, art.get('title', ''), strip_html(art.get('content', '')), art.get('digest', '')
    cpf = pa['accountForms'][0].get('contentPublishForm', {})
    title = cpf.get('title', '')
    body = cpf.get('description', '') or cpf.get('desc', '')
    body = strip_html(body) if '<' in body else body
    if content_file:
        body = strip_md(pathlib.Path(content_file).read_text())
    elif plat == '知乎' and pa.get('content'):
        body = strip_md(pa['content'])
    return plat, ptype, title, body, ''


def narration(payload_path):
    """同目录或上级目录里的动效 spec（口播稿）。"""
    for d in (payload_path.parent, payload_path.parent.parent):
        for f in d.glob('*.json'):
            try:
                sp = json.loads(f.read_text())
            except Exception:
                continue
            if isinstance(sp, dict) and isinstance(sp.get('scenes'), list) and sp['scenes'] and 'lines' in sp['scenes'][0]:
                return f, ''.join(re.sub(r'\*\*', '', ln) for sc in sp['scenes'] for ln in sc.get('lines', []))
    return None, ''


SPOKEN_BAD = ['据悉', '据报道', '援引', '表示', '进行', '该产品', '此次', '此外', '与此同时', '值得注意的是', '需要指出的是',
              '综上所述', '总的来说', '总而言之', '首先', '其次', '不难发现', '众所周知', '各位', '大家好', '今天聊聊', '今天我们']


def spec_checks(spec_f):
    """口播稿/画面编排体检（运营手册/口播稿规则.md）：能机器查的部分。"""
    errs, warns = [], []
    sp = json.loads(spec_f.read_text())
    scenes = sp.get('scenes', [])
    unit = lambda s: sum(0.55 if c.isascii() else 1 for c in re.sub(r'\*\*|\s|\[停\s*[\d.]+\s*秒?\]', '', s))
    total = 0
    for i, sc in enumerate(scenes):
        ls = [re.sub(r'\*\*|\[停\s*[\d.]+\s*秒?\]', '', x) for x in sc.get('lines', [])]
        total += sum(unit(x) for x in ls)
        n_items = len(sc.get('items') or sc.get('points') or [])
        if len(ls) > 4 and not (sc.get('type') in ('list', 'bars', 'timeline') and len(ls) <= n_items + 1):
            warns.append(f'场景{i}（{sc.get("type")}）有 {len(ls)} 句，超过 4 句中段容易流失（批次执行.md 2.4：每 8–10 秒一个新信息点），拆成两个场景')
        for x in ls:
            for seg in re.split(r'[，。？！；：,?!;]', x):
                if unit(seg) > 22:
                    warns.append(f'场景{i} 一口气 {unit(seg):.0f} 字没有停顿：「{seg[:24]}…」')
        if sc.get('type') in ('list', 'bars', 'timeline') and n_items and not sc.get('reveal') and len(ls) not in (n_items, n_items + 1):
            warns.append(f'场景{i}（{sc["type"]}）{n_items} 条但只有 {len(ls)} 句，条目没法跟着口播逐条出现（句数应为 {n_items} 或 {n_items + 1}，或写 reveal）')
        if i and sc.get('type') == scenes[i - 1].get('type') and sc.get('type') not in ('screen',):
            warns.append(f'场景{i - 1}、{i} 都是 {sc.get("type")}，相邻场景换个类型')
    narr = ''.join(re.sub(r'\*\*', '', x) for sc in scenes for x in sc.get('lines', []))
    if bad := [w for w in SPOKEN_BAD if w in narr]:
        warns.append(f'口播里有书面词/套话：{"、".join(bad)}（见 口播稿规则.md 第 4 节）')
    if scenes and scenes[0].get('lines'):
        first = re.split(r'[，。？！]', re.sub(r'\*\*', '', scenes[0]['lines'][0]))[0]
        if unit(first) > 16:
            warns.append(f'第一句「{first}」{unit(first):.0f} 字，开头 2 秒要说完（≤16 字，批次执行.md 2.4 留存结构）')
    if scenes and not any(('？' in x or '?' in x) for x in scenes[-1].get('lines', [])):
        warns.append('最后一个场景没有一个具体问题')
    if re.search(r'今天|昨天|今晚|昨晚', narr):
        warns.append('口播里有「今天/昨天」，视频可能隔天发或被其他平台复用，写具体日期')
    # human-writing skill 的成稿检查（硬禁词、翻案句、黑话、模型路标等），只报警
    chk = pathlib.Path(__import__('os').environ.get('PROSE_CHECKER', str(pathlib.Path.home() / '.codex/skills/human-writing/scripts/check_prose.py')))
    if chk.exists():
        import subprocess
        r = subprocess.run([sys.executable, str(chk), '-'], input='\n'.join(re.sub(r'\*\*', '', x) for sc in scenes for x in sc.get('lines', [])),
                           capture_output=True, text=True, timeout=60)
        m = re.search(r'翻案句 (\d+).*?黑话 (\d+)，硬停词 (\d+)，模型路标 (\d+)', r.stdout)
        if m and any(int(x) for x in m.groups()):
            warns.append('human-writing 检查：' + r.stdout.strip().splitlines()[1] if len(r.stdout.strip().splitlines()) > 1 else r.stdout.strip())
    if '：' in narr or '——' in narr:
        warns.append('口播里有冒号或破折号，TTS 停顿会生硬，改成逗号或拆句')
    return errs, warns, {'narration_units': round(total), 'est_seconds': round(total / 5.5)}


PROSE_CHECKER = pathlib.Path(__import__('os').environ.get('PROSE_CHECKER', str(pathlib.Path.home() / '.codex/skills/human-writing/scripts/check_prose.py')))
_CP = []


def _check_prose():
    """按文件加载 human-writing 的 check_prose.py（只用它的正则和统计函数）；没装/加载失败返回 None。"""
    if not _CP:
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location('_hw_check_prose', PROSE_CHECKER)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod
            spec.loader.exec_module(mod)
            _CP.append(mod)
        except Exception:
            sys.modules.pop('_hw_check_prose', None)
            _CP.append(None)
    return _CP[0]


def html_paras(s):
    """公众号 HTML → 空行分段的近似 markdown，给 check_prose 判断段落/小标题用。
    排版件（目录卡、序号徽标、图注）是没有句末标点的短行，丢掉，免得被当成「短促单句段」。"""
    s = re.sub(r'<h\d[^>]*>', '\n\n# ', s or '')
    s = re.sub(r'</(p|h\d|section|blockquote)>', '\n\n', s)
    s = re.sub(r'<br[^>]*>|</li>', '\n', s)
    blocks = [b.strip() for b in re.split(r'\n\s*\n', html.unescape(re.sub(r'<[^>]+>', '', s)))]
    return '\n\n'.join(b for b in blocks if b.startswith('# ') or re.search(r'[。！？!?…]', b) or len(b) > 30)


def prose_checks(src):
    """check_prose 的统计/形状指标，全部作为 warn，阈值照搬 check_prose.main()。
    不收它的硬禁令：全部冒号、任何破折号比 去AI味规则.md（D1 每千字≤1、D2 只禁宣布式冒号）严，破折号上面已查；
    它的黑话/硬停词/模型路标只收本脚本 AI_ERR/AI_WARN 没覆盖的。"""
    cp = _check_prose()
    if not cp or not (src or '').strip():
        return [], {}
    try:
        t = cp.mask_non_prose(src)
        han = cp.han_count(t)
        if not han:
            return [], {}
        ex = lambda m, w=28: '「' + cp.excerpt(m.group().strip('。！？!? \n'), w) + '」'
        W, st = [], {'han': han}
        cv = cp.sentence_length_cv(t)
        if cv:
            st['sent_cv'] = round(cv[0], 2)
            if cv[0] < 0.42:
                W.append(f'句长太平均：{cv[1]} 句的变异系数 {cv[0]:.2f}（<0.42），十个字的句子要能挨着四十个字的，放开几句、压短几句')
        conj = cp.non_overlapping_terms(t, cp.CONJUNCTIONS)
        st['conj_per_k'] = round(len(conj) * 1000 / han, 1)
        if han >= 600 and len(conj) * 1000 / han > 7:
            top = '、'.join(f'{k}{v}次' for k, v in collections.Counter(x for _, x in conj).most_common(4))
            W.append(f'连词密度每千字 {len(conj) * 1000 // han} 个（>7）：{top}，删一半试试')
        piv = cp.all_matches(t, cp.PIVOT_PATTERNS)
        spans, sem = [m.span() for m in piv], []
        for m in cp.all_matches(t, cp.SEMANTIC_PIVOT_PATTERNS):
            if not any(m.start() < e and m.end() > s for s, e in spans):
                sem.append(m)
                spans.append(m.span())
        if piv or sem:
            W.append(f'翻案句 {len(piv)} 处、疑似变形 {len(sem)} 处：{"、".join(ex(m) for m in (piv + sem)[:4])}，先立误解再推翻的改成正面陈述，正常用法保留')
        if an := cp.anaphora_runs(t):
            W.append(f'三连以上同构排比 {len(an)} 处：{"、".join(ex(m) for m in an[:2])}，留两项')
        if nm := cp.all_matches(t, cp.NOMINALIZATION_PATTERNS):
            W.append(f'名词化 {len(nm)} 处：{"、".join(ex(m, 20) for m in nm[:4])}，还原成直接的动词')
        if len(ly := cp.non_overlapping_terms(t, cp.LYRIC_WORDS)) >= 2:
            W.append(f'模型偏爱的抒情词 {len(ly)} 处：{"、".join(dict.fromkeys(x for _, x in ly))}')
        if len(hl := cp.bracket_highlights(t)) > max(3, han // 700):
            W.append(f'「」括起的短语 {len(hl)} 处：{"、".join(dict.fromkeys(m.group() for m in hl[:6]))}，太密像在批量造金句')
        if len(mk := cp.non_overlapping_terms(t, cp.SOFT_MARKERS)) > max(2, han // 900):
            W.append(f'洞察路标 {len(mk)} 处（提醒线 {max(2, han // 900)}）：{"、".join(dict.fromkeys(x for _, x in mk))}')
        if len(lb := cp.all_matches(t, cp.LEFT_BRANCH_PATTERNS)) > max(2, han // 1200):
            W.append(f'长前置成分 {len(lb)} 处，主干来得太晚：{"、".join(ex(m) for m in lb[:3])}')
        if len(dd := cp.heavy_de_sentences(t)) > max(1, han // 1500):
            W.append(f'{len(dd)} 个长句含四个以上「的」，先交代人和动作：{"、".join(ex(m) for m in dd[:3])}')
        paras = cp.prose_paragraphs(t)
        if len(paras) >= 10 and (r1 := sum(p.sentences <= 1 for p in paras) / len(paras)) >= 0.75:
            W.append(f'{r1:.0%} 的段落只有一句话，形成统一的短段鼓点')
        if sk := cp.short_streak(paras):
            W.append(f'连续 {len(sk)} 个短促单句段（从「{cp.excerpt(sk[0].text, 16)}」起），检查是不是在排队喊结论')
        cnt, _ = cp.opener_counts(paras)
        if rep := [f'{k}{v}次' for k, v in cnt.items() if v >= 4]:
            W.append(f'段落开场重复：{"、".join(rep)}')
        if mc := cp.metaphor_cluster(t):
            W.append(f'八百字内 {len(mc[1])} 套借喻（{"、".join(sorted(mc[1]))}）：{"、".join(dict.fromkeys(h[2] for h in mc[0]))}')
        terms = [x for _, x in cp.non_overlapping_terms(t, cp.HARD_STOPS + cp.HARD_JARGON)]
        terms += [next((p for p in cp.ROAD_SIGNS if p in m.group()), m.group()) for m in cp.all_matches(t, cp.ROAD_SIGN_PATTERNS)]
        if terms := [x for x in dict.fromkeys(terms) if not any(re.search(p, x) for p in AI_ERR + AI_WARN)]:
            W.append(f'黑话/路标：{"、".join(terms)}')
        return ['活人感·' + w for w in W], st
    except Exception:
        return [], {}


def lint(payload_path, content_file=None):
    payload_path = pathlib.Path(payload_path).resolve()
    o = json.loads(payload_path.read_text())
    plat, ptype, title, body, digest = extract(o, content_file)
    rule = RULES.get(plat, RULES['新浪微博'])
    rv = payload_path.parent / 'review.md'
    allow = set()
    if rv.exists():
        for m in re.finditer(r'lint-allow[:：]\s*(.+)', rv.read_text()):
            allow |= {x.strip() for x in re.split(r'[,，、\s]+', m.group(1)) if x.strip()}
    errs, warns = [], []

    def hit(pats, text):
        out = []
        for p in pats:
            for m in re.finditer(p, text):
                if m.group(0) not in allow and not any(a in m.group(0) for a in allow):
                    out.append(m.group(0))
        return sorted(set(out))

    # 栏目（00-必读 2.2.5）：没有栏目，数据回流、工作台和进化都只能归到「未标」
    if payload_path.name.endswith('.payload.json'):
        pj = payload_path.with_name(payload_path.name[:-len('.payload.json')] + '.json')
        if pj.exists():
            try:
                col = (json.loads(pj.read_text()) or {}).get('column')
            except Exception:
                col = None
            if not col:
                errs.append(f'{pj.name} 没写 "column"：按 内容总纲.md 的栏目填（如 "column": "热点"），不然这条数据没法按栏目归因')
    # 标题
    tl = len(title)
    if title and tl > rule['title_max']:
        errs.append(f'标题 {tl} 字，超过 {plat} 上限 {rule["title_max"]}')
    if plat == '微信公众号' and tl > 30:
        warns.append(f'公众号标题 {tl} 字，订阅号列表里超过约 30 字会被截断')
    if h := hit([re.escape(w) for w in HYPE], title):
        errs.append(f'标题含营销词：{"、".join(h)}')
    if title and '！！' in title:
        errs.append('标题连用感叹号')
    if title and not re.search(r'\d|[A-Za-z]{2,}', title) and plat != '微信公众号':
        warns.append('标题没有数字或具体产品名，具体度偏低')
    # 正文
    text = title + '\n' + body + '\n' + digest
    if h := hit(AI_ERR, text):
        errs.append(f'AI 腔（必须改）：{"、".join(h)}')
    if h := hit(AI_WARN, text):
        warns.append(f'疑似 AI 腔（逐个确认）：{"、".join(h)}')
    if h := hit([re.escape(w) for w in HYPE], body):
        warns.append(f'正文含营销词：{"、".join(h)}')
    if h := hit(PLACEHOLDER, text):
        errs.append(f'疑似占位符/未完成：{"、".join(h)}')
    if '！！' in body or '!!' in body:
        errs.append('正文连用感叹号')
    dash = body.count('——') + body.count('--')
    n = max(len(body), 1)
    if dash and dash / n * 1000 > 1.5:
        warns.append(f'破折号 {dash} 处（每千字应 ≤1）')
    emo = len(EMOJI_RE.findall(body))
    if emo > rule['emoji']:
        (errs if emo > rule['emoji'] + 2 else warns).append(f'正文 emoji {emo} 个，{plat} 建议 ≤{rule["emoji"]}')
    if plat in ('抖音', '视频号', '小红书', '新浪微博', '哔哩哔哩-Open') and re.search(r'\*\*|^#{1,3} |```', body, re.M):
        errs.append('纯文本平台出现 markdown 符号（** / ## / ```）')
    tags = TAG_RE.findall(body) if plat in ('抖音', '视频号', '小红书', '新浪微博') else []
    if plat == '哔哩哔哩-Open':  # B站标签在 tags 数组里，不在描述里
        tags = o['publishArgs']['accountForms'][0]['contentPublishForm'].get('tags', [])
        if long := [t for t in tags if len(t) > 20]:
            errs.append(f'B站标签超过 20 字：{"、".join(long)}')
    lo, hi = rule['tags']
    if plat in ('抖音', '视频号', '小红书', '新浪微博', '哔哩哔哩-Open') and not lo <= len(tags) <= hi:
        warns.append(f'话题 {len(tags)} 个，{plat} 建议 {lo}–{hi} 个')
    plain = re.sub(TAG_RE, '', body)
    blen = len(re.sub(r'\s', '', plain))
    if ptype != 'video' and not rule['body'][0] <= blen <= rule['body'][1]:
        warns.append(f'正文 {blen} 字，{plat} 建议 {rule["body"][0]}–{rule["body"][1]}')
    if rule['ask']:
        tail = [x for x in plain.strip().split('\n') if x.strip()][-2:]
        if not any(('？' in x or '?' in x) for x in tail):
            warns.append('结尾没有一个具体问题引导评论')
    if body.count('我们') > 6:
        warns.append(f'「我们」出现 {body.count("我们")} 次，示例作者说话用「我」「你」')
    # 活人感指标（human-writing/check_prose），优先用保留段落结构的原文：正文文件 > 公众号 HTML > 知乎 markdown > 去掉话题的正文
    pa = o['publishArgs']
    if content_file:
        src = pathlib.Path(content_file).read_text()
    elif plat == '微信公众号' and o.get('publishType') != 'imageText':
        src = html_paras(pa['platformForms'][plat]['articles'][0].get('content', ''))
    elif plat == '知乎' and pa.get('content'):
        src = pa['content']
    else:
        _f = pa['accountForms'][0].get('contentPublishForm', {}); d = _f.get('description', '') or _f.get('desc', '')
        src = re.sub(TAG_RE, '', html_paras(d)) if '<' in d else plain
    pw, pst = prose_checks(src)
    warns += [w for w in pw if not any(a in w for a in allow)]
    # 口播稿
    spec_f, narr = narration(payload_path) if ptype == 'video' else (None, '')
    stats = {'platform': plat, 'type': ptype, 'title_len': tl, 'body_len': blen, 'tags': len(tags), 'emoji': emo}
    if pst:
        stats['prose'] = pst
    if narr:
        if '——' in narr:
            errs.append(f'口播稿有破折号（{spec_f.name}），TTS 会读断')
        if h := hit(AI_ERR, narr):
            errs.append(f'口播 AI 腔（必须改）：{"、".join(h)}')
        if h := hit(AI_WARN, narr):
            warns.append(f'口播疑似 AI 腔：{"、".join(h)}')
        if EMOJI_RE.search(narr):
            errs.append('口播稿里有 emoji')
        stats['narration_chars'] = len(narr)
        e2, w2, st2 = spec_checks(spec_f)
        errs += e2
        warns += [w for w in w2 if not any(a in w for a in allow)]
        stats.update(st2)
    return {'errors': errs, 'warns': warns, 'stats': stats}


if __name__ == '__main__':
    a = sys.argv[1:]
    cf = a[a.index('--content-file') + 1] if '--content-file' in a else None
    r = lint(a[0], cf)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    sys.exit(1 if r['errors'] else 0)
