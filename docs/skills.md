# 技能依赖与来源

本仓库自有编排技能在 `skills/`。以下第三方技能供选择安装，原文不随 MIT 代码重新分发。指纹记录本次本地版本，不能替代上游签名或版本发布。未有可靠来源链接的条目按精确技能名在宿主技能目录或 SkillHub 搜索，并确认作者与许可；不猜测仓库地址。

| 技能 | 来源 | 用途 |
|---|---|---|
| `human-writing` | 按精确技能名查询作者来源 | 见公开版技能地图与上游说明 |
| `humanizer-zh` | [上游](https://github.com/op7418/Humanizer-zh) | 见公开版技能地图与上游说明 |
| `humanizer` | [上游](https://github.com/blader/humanizer) | 见公开版技能地图与上游说明 |
| `content-compliance-checker` | [上游](https://github.com/mengbao/content-compliance-checker) | 逐平台候选词与语境检查 |
| `xy-opener` | [上游](https://skillhub.cn/skills/user_93c42d4c/xy-opener) | 见公开版技能地图与上游说明 |
| `xy-script-glue` | [上游](https://skillhub.cn/skills/user_93c42d4c/xy-script-glue) | 见公开版技能地图与上游说明 |
| `opc-short-video-review` | [上游](https://skillhub.cn/skills/user_ccb113d8/opc-short-video-review) | 见公开版技能地图与上游说明 |
| `dbs-xhs-title` | 按精确技能名查询作者来源 | 见公开版技能地图与上游说明 |
| `zhihu-answer-master` | [上游](https://skillhub.cn/skills/douease/zhihu-answer-master) | 见公开版技能地图与上游说明 |
| `wechat-article-craft` | [上游](https://skillhub.cn/skills/user_a95aac1d/wechat-article-craft) | 见公开版技能地图与上游说明 |
| `dbskill-dontbesilent` | [上游](https://skillhub.cn/skills/user_13deaa5f/dbskill-dontbesilent) | 见公开版技能地图与上游说明 |
| `aihot` | 按精确技能名查询作者来源 | 见公开版技能地图与上游说明 |
| `easel-social-cards` | [上游](https://github.com/ZJU-REAL/Easel) | 见公开版技能地图与上游说明 |
| `card-design` | 按精确技能名查询作者来源 | 见公开版技能地图与上游说明 |
| `card-xiaohongshu` | 按精确技能名查询作者来源 | 见公开版技能地图与上游说明 |
| `card-quote` | 按精确技能名查询作者来源 | 见公开版技能地图与上游说明 |
| `comparison-card` | 按精确技能名查询作者来源 | 见公开版技能地图与上游说明 |
| `poster-hero` | 按精确技能名查询作者来源 | 见公开版技能地图与上游说明 |
| `blcaptain-style-skill` | [上游](https://github.com/dososo/blcaptain-style-skill) | 见公开版技能地图与上游说明 |
| `guizang-social-card-skill` | [上游](https://github.com/op7418/guizang-social-card-skill) | 见公开版技能地图与上游说明 |
| `hyperframes` | 按精确技能名查询作者来源 | 见公开版技能地图与上游说明 |
| `hyperframes-core` | 按精确技能名查询作者来源 | 见公开版技能地图与上游说明 |
| `hyperframes-creative` | 按精确技能名查询作者来源 | 见公开版技能地图与上游说明 |
| `hyperframes-animation` | 按精确技能名查询作者来源 | 见公开版技能地图与上游说明 |
| `hyperframes-audio` | 按精确技能名查询作者来源 | 见公开版技能地图与上游说明 |
| `hyperframes-cli` | 按精确技能名查询作者来源 | 见公开版技能地图与上游说明 |
| `hyperframes-registry` | 按精确技能名查询作者来源 | 见公开版技能地图与上游说明 |
| `hyperframes-keyframes` | 按精确技能名查询作者来源 | 见公开版技能地图与上游说明 |
| `faceless-explainer` | 按精确技能名查询作者来源 | 见公开版技能地图与上游说明 |
| `media-use` | 按精确技能名查询作者来源 | 见公开版技能地图与上游说明 |
| `yixiaoer` | 按精确技能名查询作者来源 | 见公开版技能地图与上游说明 |
| `gzh-design` | [上游](https://github.com/isjiamu/gzh-design-skill) | 见公开版技能地图与上游说明 |
| `wechat-layout` | 按精确技能名查询作者来源 | 见公开版技能地图与上游说明 |

content-compliance-checker 的参考上游提交为 `760690edfe16050a1a52609dd89a0b4ca85f23ae`。它是提示词技能，不是扫描程序；没有微博/知乎/B站专用词库。逐平台检查方法见 [发布前违禁词检查](../运营手册/发布前违禁词检查.md)。

安装固定版本示例（使用已安装的 Codex skill-installer）：

```bash
python3 /path/to/skill-installer/scripts/install-skill-from-github.py --repo mengbao/content-compliance-checker --ref 760690edfe16050a1a52609dd89a0b4ca85f23ae --path . --name content-compliance-checker
```

SkillHub 来源可使用 `skillhub --skip-self-upgrade --dir /path/to/skills install <slug> --namespace <author>`。先读完整 SKILL.md 与脚本，核对许可、网络请求和凭据访问；升级先在临时目录审查 diff。各宿主具体安装路径以自身配置为准。

写作主线：human-writing → 平台技能 → humanizer-zh → content-compliance-checker + 素材人工复核 → lint。卡片与视频技能为可选辅助，现有 Python/HTML 工具仍是主渲染链。gzh-design、wechat-layout 保留为排版参考，当前红色主题工具为 gzh_red.py。

对于会把检索词发给外部服务的技能，优先使用其明确支持的本地模式；不要将稿件、账号或凭据作为检索词发送。第三方技能的推广、默认人设、发布时间、付费调用及要求停顿的交互策略，不自动覆盖使用者的运营规则。

完整机器可读清单见 [skills-manifest.json](skills-manifest.json)。

## 技能与两站的配合

从 [灵策AI热点](https://aihot.lynxce.cn/) 获取候选与原文，在 [灵策 Web](https://web.lynxce.cn/) 注册登录后写稿与制作素材。Agent 用技能组织这些任务：aihot 辅助信息发现，human-writing 起草，平台技能适配，humanizer-zh 改稿，再执行逐平台用词复核。不要把工具生成结果当成已经审核或公开。

AIHOT 当前接入方式见 [Agent 页](https://aihot.lynxce.cn/agent)；使用已有 aihot 技能时，应核对它支持的服务地址，不把上游 aihot.news 的默认地址当作已经接入此站。可以按 [workflow.md](workflow.md) 直接配置灵策AI热点 MCP 或本地雷达的 `AIHOT_API_BASE`。

### 后续技能变更

依赖清单同时记录 SKILL.md 指纹与技能文本、脚本、参考资料的目录摘要（tree_sha256），便于发现更新；本地缓存、依赖包和私人运行记录不纳入目录摘要。指纹不等于官方版本或许可，变更后仍需核对来源、审查实际差异，并同步修改平台技能地图及接入说明。
