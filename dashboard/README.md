# 矩阵运营工作台

多平台自媒体矩阵的本地只读看板，内容包括：粉丝增长和目标进度、每个账号的投入产出、周排期和 30 天发布心跳、发布成功率和失败原因、内容台账（成品图、视频、文案、审稿记录）、作品数据（播放、2 秒跳出、5 秒完播）、互动额度、热点雷达、运营手册、A/B 实验、版本时间线、日报。

- **零依赖**：服务端只用 Python 标准库（3.9+），前端是原生 JS，没有构建步骤。图表用本地的 ECharts，markdown 渲染用可选的 `markdown-it-py`，不装也能用。
- **只读**：sqlite 用 `mode=ro` 打开；不调用任何发布、互动或付费接口；不读 `.env`；默认只监听 `127.0.0.1`。
- **单个数据源坏了只影响一块**：读不到的区块显示空状态，接口照样返回 200，错误写在 `errors` 字段里。

## 快速开始

```bash
# 用示例数据跑（8 个虚构账号、21 天历史，自动生成到 dashboard/demo/sample，不碰任何真实数据）
python3 dashboard/server.py --demo

# 用自己的数据目录跑
python3 dashboard/server.py --root /path/to/ops-root --port 8790
```

打开 <http://127.0.0.1:8790>。页面每 60 秒自动刷新，只有变化的数字会滚动并闪一下，首次加载直接显示真实数值。

| 参数 | 环境变量 | 默认 |
|---|---|---|
| `--root` | `MATRIX_ROOT` | `dashboard/` 的上一级目录 |
| `--port` | `DASH_PORT` | 8790 |
| `--host` | `DASH_HOST` | 127.0.0.1。改成局域网地址时，同一网络里的设备都能看到数据，会打印提醒 |
| `--demo` | | 示例数据，跨天会自动重新生成 |

## 页面

| 页面 | 看什么 |
|---|---|
| 总览 | 运营简报（下一批发布、数据状态、最新日报）、粉丝总数（较昨日、较 7 天）、目标进度、今日发布进度、待处理（带失败原因归类和处理建议）、账号卡片、24 小时排期、热点前五、任务运行、互动、手册版本 |
| 增长 | 粉丝总数走势、各账号净增、自动结论（谁涨得多、谁发了不涨、谁没发满），以及投入产出表：每条涨粉、每千播放涨粉、完成率、失败数、均播放、互动率。可导出 CSV |
| 日历 | 周排期（账号 × 7 天，缺几条一眼看到）、30 天发布心跳、每天发布结果和成功率、发布方式的一次成功率、失败原因（按报错文字归类，带处理建议和涉及账号） |
| 内容 | 按天看卡片或列表，可按平台、状态、栏目筛选，也可在当天内搜文字。抽屉里能看成品图、视频、文案、正文、审稿、作品数据和流程记录 |
| 数据 | 近 7、14、30、90 天的作品数据，KPI 和上一期对比，各平台每日播放、栏目对比、发布时段、开头留存、汇总表，作品明细可排序、筛选、导出 CSV |
| 账号 | 单个账号的粉丝走势、近 7 天作品数据和诊断、台账 |
| 互动 | 各平台各动作的已用次数和上限、互动流水 |
| 热点 | 最新一轮雷达候选（综合分、跨平台热度、切入角度）、快反记录 |
| 运营计划 | 当前计划、手册（浏览整个手册目录，带目录导航）、实验看板、版本时间线、数据进化、任务运行 |
| 日报 | 晚间复盘与全天报告列表、目录阅读、Markdown 下载及打印 |

右上角的「数据源」标签显示每个数据源最后一次更新的时间。某个数据源超过预期节奏还没更新、或者手册当天升版过多时，标签会变黄，点开能看到具体是哪一个、应该怎么查。

## 快捷键

| 键 | 作用 |
|---|---|
| `⌘K` / `Ctrl+K` / `/` | 命令面板：搜内容标题、日报、手册全文，跳页面或账号，执行操作 |
| `1`–`9`、`0` | 按侧栏顺序切换页面 |
| `R` | 刷新 |
| `T` | 深浅色：跟随系统 → 浅色 → 深色 |
| `[` `]` | 前一天、后一天（日历页是前一周、后一周） |
| `←` `→` | 内容详情里切上一条、下一条 |
| `C` / `O` | 内容详情里复制标题 / 打开原帖 |
| `?` | 快捷键表 |

地址栏会保存页面状态，包括筛选条件和打开的那条内容（`#/content?day=…&item=…`），可以收藏，也可以发给别人，刷新后状态还在。

## 配置（可选）

在 `config/dashboard.json` 里写配置，没有这个文件就用默认值：

```json
{
  "title": "我的矩阵",
  "subtitle": "运营工作台",
  "goal": { "fans": 10000, "by": "2026-12-31", "label": "年底 1 万粉" },
  "manual_dir": "运营手册",
  "manual_index": "00-必读.md",
  "manual_plan": "运营计划.md",
  "manual_changelog": "变更日志.md",
  "manual_skip": ["存档"],
  "max_bumps_per_day": 4,
  "health": { "fans": 1560, "metrics": 840, "radar": 90, "runs": 240 }
}
```

- `goal`：配了才显示目标进度。进度条会给出剩余天数、需要的日均增长、按近 7 天的速度还要多少天，以及当前是否落后。
- `health`：每个数据源允许多少分钟不更新，超过就提醒。照自己定时任务的节奏改。

## 数据目录约定

工作台只读下面这些文件，缺了的部分显示空状态。接入自己的系统时按这个结构写数据就行，`dashboard/demo/make_demo.py` 是一份能跑的完整示例。

```
config/schedule.json        accounts: {slot: {platform, name, account_id, times[], weekdays_only?, weekdays?[0=周一], paused?, metrics_account?}}
config/experiments.json     experiments: [{id, title, status, arms{}, metric, direction, min_n, start, review, platforms[]}]
config/dashboard.json       看板配置（见上）
state/ops.sqlite3           items(id, day, slot, platform, publish_type, due, mode, status, payload, title, url, detail, updated)
                            events(at, item, kind, data)
state/metrics.sqlite3       snaps(platform, account, post_id, title, created, snap, m JSON)
state/fans.json             {account_id: 粉丝数}
state/fans_history.jsonl    {"at": ISO, "day": "YYYY-MM-DD", "fans": {account_id: n}}
days/<日期>/<内容>/post.json  title, column, images[], cover, video, description, tags
days/<日期>/radar/*.json     {at, total, new, candidates: [{title, score, cross_score, sources, angle, url}]}
days/<日期>/runs.jsonl       {at, task, event: start|end, version, summary}
days/<日期>/engagement.jsonl {time, platform, action, target, text, note}
days/<日期>/evolve.json      {suggestions[], quality[], dims[], platform_baseline{}}
days/<日期>/zhihu-answers.md  Markdown 表格：时间 | 问题 | 栏目 | 链接 | 备注
reports/<日期>.md            日报
<manual_dir>/*.md           运营手册（00-必读.md 里写「版本：vYYYY.MM.DD-N」）
scripts/engage.py           CAPS = {平台: {动作: 每日上限}}，用 AST 读取，不执行
scripts/metrics.py          可选，有 diagnose_one(x) 就用来给作品写诊断
```

## 口径

- **状态分组**
  - 已发：success（平台报成功）、public、web；只有 public/web 且有链接才纳入总览的已核验公开。
  - 排队：draft、checked、ready、submitting、submitted，加上还没到点的 scheduled。
  - 失败：failed、blocked。
  - 待核实：uncertain，以及已到点但尚未回读确认的 scheduled。
  - 其他：platform_draft、deleted_dup、withdrawn，不算进进度。
- **已重提**：一条失败的内容，如果同一天同账号有另一条正常条目，并且标题相同、payload 相同或时间相同，就视为已经被替代，不再算失败。备注里写了「已撤、已取消、已处理」之类字样的也视为已处理。
- **按内容计**：增长页和日历页把同一天、同账号、同标题的多次尝试算成一条内容，只要有一次发出去就算成功。成功率 = 发出 ÷（发出 + 最终失败）。一次成功 = 第一次提交就发出。
- **失败原因**：用报错文字归成 6 类，依次是登录失效、网络/代理、账号配置、审核/风控、素材/参数、超时，前面的优先匹配；都对不上的算「其他」。
- **应发**：每个账号在台账里第一次出现之后才开始算。每天应发条数等于 `times` 里的时段数；`weekdays_only` 的账号周末为 0，写了 `weekdays`（0=周一）的账号只在那几天算，`paused` 的账号为 0。配额是下限，发多了算正常。
- **粉丝**：当前值以 `state/fans.json` 为准，历史取每天最后一次采集，缺数据的日子沿用前一天。多个发布位共用一个账号时，总数只算一次。
- **作品 ↔ 台账匹配**：依次尝试三种方式：链接里的作品 id；标题前 12 字，且同平台、发布日相差不超过 1 天；同账号发布时间相差不超过 40 分钟。还没发出的内容不按标题匹配，免得把同题的旧作品认成它。
- **上一期对比**：拿前一个同样长度的窗口来比。老作品的快照通常更完整，所以这个对比只作参考。

完整自然日报可另存 `reports/<日期>.full.md`，同一天优先显示完整报告，`.regen.md` 不纳入列表。完整报告应覆盖北京时间 00:00–24:00，指标附采集口径。

## 接口

`GET /api/` 下的接口：`overview`、`growth?days=`、`calendar?start=&days=`、`content?day=&platform=&status=&column=`、`content/<id>`、`metrics?days=`、`accounts`、`fans`、`engagement?day=`、`hot?day=`、`plan`、`docs`、`docs?path=`、`reports`、`reports/<日期>`、`search?q=`、`health`、`meta`。

`GET /files/<相对路径>` 只放行 `days/` 和 `assets/` 下的图片和 mp4。路径 resolve 之后必须还在这两个目录里，否则一律返回 404。mp4 支持 Range 请求，可以拖动进度条。`docs?path=` 只放行手册目录下的 `.md`。

## 前端约定

- **配色**：界面本身保持冷灰单色，颜色只用来表示平台身份和状态语义。状态都是「图形 + 文字」，从不只靠颜色表达。
- **动效**：用浏览器原生 Web Animations API，不依赖第三方库。全站只用一条缓动曲线，只动 transform 和 opacity。系统开了「减少动态效果」，或者页面在后台标签页时，直接显示最终状态。
- **浏览器本地存储**：只存个人偏好，包括深浅色、内容视图、最近打开、热点「新上榜」的记录。读写失败时页面照常工作。
- **第三方文件**：放在 `static/vendor/`，出处、许可证和校验值见 `static/vendor/README.md`。

## 远程只读站（手机上看）

`--auth <配置>` 打开登录后，可以把工作台放到公网服务器上。这时没有登录的人什么都看不到：页面跳到 `/login`，接口和图片一律返回 401。

- **登录方式**：配置里 `provider: "provider"` 表示用示例服务账号登录，可以用短信验证码（服务端代调 `/api/auth/phone-code`、`/api/auth/phone-login`），也可以用账号密码（`/api/auth/password-login`，账号填手机号或邮箱），不改示例服务后端。示例服务的 POST 接口成功时返回 HTTP 201，所以按 2xx 且 `code` 为 0 判断成功。
- **白名单**：只有 `allow` 里的手机号才会触发发码，名单外的号码在调示例服务之前就被拦下。原因是示例服务的验证码登录遇到新号码会自动注册。
- **绑定用户**：第一次登录时会记下这个号码对应的示例服务用户 id，之后必须一致。
- **会话**：本站自己签发 cookie（HMAC 签名，HttpOnly、Secure、SameSite=Lax，默认 7 天），号码从名单里删掉后立即失效。登录相关请求有频率限制，还会校验 Origin。

数据由 `scripts/dashboard_sync.py`（本机 launchd 每小时跑一次）推到服务器：

- **数据库**：sqlite 先用 backup API 做一致性快照，并转成非 WAL 模式，因为 WAL 库在只读挂载上打不开。
- **视频**：只推最近 3 天的。
- **保留天数**：日期目录只保留最近 45 天。
- **不推的文件**：`.env`、登录二维码截图、发布回执、渲染缓存。

远程部署需自行提供容器或服务管理配置、HTTPS 反向代理和符合上述协议的认证服务；本仓库不附带原服务器配置。

## 常驻运行（可选）

macOS 用 launchd，Linux 用 systemd，让服务开机自启、挂了自动拉起。下面是 launchd 的示例，把路径换成你自己的：

```xml
<!-- ~/Library/LaunchAgents/local.matrix-dashboard.plist -->
<plist version="1.0"><dict>
  <key>Label</key><string>local.matrix-dashboard</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/python3</string>
    <string>/path/to/matrix-ops-dashboard/dashboard/server.py</string>
    <string>--root</string><string>/path/to/your/ops</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict></plist>
```

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.matrix-dashboard.plist
launchctl kickstart -k gui/$(id -u)/local.matrix-dashboard   # 改了 server.py 后重启
```

改了 `static/` 里的前端文件，刷新页面就能看到。
