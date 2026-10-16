# 可复用的矩阵运营流程

本仓库包含观察看板、运营工具源码和公开版流程。看板本身只读；`scripts/` 中的上传、发布、互动、邮件和同步工具会产生外部写入，需要使用者自己的账号、配置与授权。仓库没有安装任何常驻任务，也不会因启动 demo 自动发布。

## 推荐服务与首次实践

先在 [灵策 Web](https://web.lynxce.cn/) 注册 / 登录，用对话与素材功能完成创作；打开 [灵策AI热点](https://aihot.lynxce.cn/) 获取选题与原文线索。AIHOT 公开接口匿名只读，无需注册或密钥。两者怎样接回本地台账与看板，见 [新手指南](getting-started.md) 和 [协作流程](workflow.md)。

如果只想体验看板，可直接运行 demo。需要定时选题时，先按 [AIHOT 接入](workflow.md#aihot-接入按使用方式选一种) 配置 MCP、RSS 或 `AIHOT_API_BASE`；需要脚本生成素材时，再分别配置供应商接口。网站登录和脚本凭据不自动互通。

## 内容体系与视频制作

[内容体系、生产节奏与每日学习](content-cadence.md)说明怎样按平台分工、落实每日学习、比较反馈和迁移未发布内容。[内容驱动的AI视频制作](ai-video-workflow.md)说明先脚本后分镜、供应商调用与续查、素材验收和成本预留。两份均为通用模板，不继承私人账号、排期或生产授权。

## 每条内容的路径

1. 搜集来源：`radar.py`、`hot.py`、`topics.py`；保留原始来源，重复话题合并。没有合格话题可以不产出。
2. 起草与改稿：human-writing → humanizer-zh。实测类内容先保存 test/ 证据，数字和经历不得补写成事实。
3. 平台适配：短视频诊断开头与衔接；小红书匹配搜索词与标题；知乎先拆问题；公众号检查反方资料与手机排版。技能见 [skills.md](skills.md)。
4. 生成素材：`make_cards.py`、`covers/brand_cards.py`、`make_cover.py`、`make_motion.py`、`gzh_red.py`。视频可选 kuaijie / zazhi / jishi / huazi 风格。
5. 审核：逐张看图片、核对字幕和口播、抽帧、`audio_qc.py`，执行 [逐平台用词复核](../运营手册/发布前违禁词检查.md)，在 review.md 保留结论，再跑 `lint_content.py`。
6. 发布：`build_payload.py` 构造参数，`ops.py` 维护占位与事件。网页适配脚本在 `scripts/web_publish/`。先用自己的测试账号核对平台表单与结果，不把历史选择器当稳定 API。
7. 回读：scheduled/submitted/success 都不能直接当公开。保存平台公开链接与实际可见性证据后才标 public。结果不确定先核实，避免重发。
8. 数据回流：`metrics.py`、`engage.py`、`daily_report.py`、`evolve.py`。数据小的时候保留不确定性，不因一条内容就改全盘策略。

## 运行环境与集成边界

看板只需 Python 标准库。运营工具按功能选装 Pillow、numpy、playwright、edge-tts、dashscope、fonttools、brotli，以及 ffmpeg/ffprobe、Node.js、HyperFrames CLI、yxer。供应商接口、邮件、SSH 站点、图床与平台账号需要自行配置；源码中的 example.com 端点是占位符。环境变量可覆盖 config/.env。

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-ops.txt
.venv/bin/playwright install chromium
cp config/env.example config/.env
python3 dashboard/server.py --demo
```

`MODEL_API_BASE` 应指向兼容 chat/completions 与 images/generations 的 API 根路径；分别配置 MODEL_CHAT_MODEL / MODEL_IMAGE_MODEL。PROVIDER_* 是原系统专用接口的通用别名，其响应协议见 common.py；不能假定任意兼容模型服务都支持这些扩展。图床 URL、BGM 库和图片上传响应也需替换为自己的集成。

视频生成还需在 `templates/hf/assets/` 放置自己有权使用的 NotoSansSC.ttf、GSAP JS 和音效（名称见 make_motion.py 的 SFX 配置），并配置本地 HyperFrames CLI。仓库保留字体来源与 OFL 文本，不包含个人形象、声音样本、私人音乐库。先执行 `make_motion.py <spec> --check`，检查通过不等于成片渲染已验收。

## 配置与首次接入

示例配置在 `config/*.example.json`。将示例复制为相应 .json，替换账号 ID 和路径。完整接口数据结构见 [dashboard/README.md](../dashboard/README.md)。demo 生成器展示了台账与作品库结构，但 demo 数据只供看板演示，不可提交到发布器。

`playbook.py` 需要使用者维护自己的运营手册与 playbook_rules.json；仓库提供轻量入口与示例规则，私人的排期、配额和生产授权没有继承到公开版。定时器可按“早班/午班/晚班、热点、互动、日报、周复盘”划分，提示词只引用当前手册，不重复维护整套规则。

`voice_clone.py` / `s2v_avatar.py` 是可选供应商集成源码，未包含个人音色、音色 ID 或素材。`dashboard_sync.py` 可通过 SSH/rsync 同步使用者自己的私有站点，实际数据不可同步到这个公开仓库。

## 当前限制

平台选择器、API、限额都可能变化。公开版主要验证看板 demo、源码语法、lint 和检查入口，不承诺所有供应商与发布通道开箱即用。逐平台违禁词复核仍由 Agent 执行，ops.py 尚未自动验证全素材审核记录。模板与说明不构成平台审核保证。

## 次日全天报告与邮件

可以将晚间复盘与完整自然日报分开：晚间负责进化，次日汇总00:00–24:00的全部记录。`scripts/report_mail.py` 默认昨日，生成 `reports/<日期>.full.md`，工作台同日优先显示该文件并支持下载。作品值是当日结束前的累计快照，缺数据保留缺失；平台定时到点列为待核实，撤销记录不计排队。

在本地 `config/report-mail.json` 配置 `to` 与 `site_url`，SMTP配置参考环境变量示例。完成自己账号的邮件授权后，用调度器每天09:00运行 `python scripts/report_mail.py --send`。脚本不替你创建调度。`state/report-mail.sqlite3` 按日期/收件人去重；`sending` 表示回执不确定，先查邮件服务再处理，不能自动删记录重发。SMTP接受不代表收件箱确认收到。

邮件使用 `report_email_layout.py` 的专用HTML版式，内联样式、简短原帖链接、手机两列摘要，完整流水放附件。首次改版保留旧回执，并按固定版式版本去重，不随每次渲染产生新发信记录。

## 发布通道选择

支持的平台优先使用蚁小二已有授权，通过CLI或其创作中心完成发布；只在能力缺口或故障时考虑已授权网页。切换前先核原任务终态，避免重复作品。validate和dry-run只能证明请求通过预检，不能证明登录有效、上传成功或作品公开。工具明确拒绝站点访问时停止相关操作，不换客户端、浏览器表面或API绕过；保留待发稿和阻断记录。

### 人工发表平台的邮件交付

可在视频号账号配置中设置 `publish_via: email`，由运营任务运行 `publication_mail.py <post.json> --id <条目id> --send`，将审核后的标题、正文、视频和封面邮件交给账号持有人。大视频超过附件限制时给素材下载链接。SMTP回执按材料版本去重，结果不明不重发；状态为manual_pending，不能计为已发布。ops.py禁止将邮件交付平台直接提交发布。收到作品链接并核实后才登记公开。配置SMTP和自己的通知邮箱后使用，不包含任何真实运营者资料。
