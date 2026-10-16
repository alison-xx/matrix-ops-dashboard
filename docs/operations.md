# 可复用的矩阵运营流程

本仓库包含观察看板、运营工具源码和公开版流程。看板本身只读；`scripts/` 中的上传、发布、互动、邮件和同步工具会产生外部写入，需要使用者自己的账号、配置与授权。仓库没有安装任何常驻任务，也不会因启动 demo 自动发布。

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
