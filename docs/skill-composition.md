# 技能筛选与组合指南

技能按内容缺口选择，每个环节保留一个主执行链。新增技能应解决明确问题，而不是增加另一套人设、台账、调度或发布通道。本页是自写的组合建议，不包含上游代码、提示词或研究镜像。

本次在 2026-10-17 对 25 个目标做了文档筛选，未安装新技能、未执行上游代码，也未进行出图、成片或发布测试。两个 ECC 子技能分别计为目标。完整来源、许可摘要、维护时间与状态见 [机器可读目录](skill-screening.json)。

## 怎样理解目录状态

- **方法借鉴**：将通用审稿、复盘或验收思路融入现有流程，不等于安装该仓库。
- **沿用已有**：研究环境已有相关工具；使用者仍需自行配置。它不表示本公开仓库捆绑工具，也不证明最新上游版本已验收。
- **候选采用**：功能可补位，但尚未安装或验证。只选需要的子技能。
- **暂缓 / 许可暂缓**：能力重叠、运行条件或许可尚待解决，保持候选状态。
- **排除商业接入**：当前许可不适合本指南的商业内容生产场景；如另获授权可重新评估。

## 让方法进入现有流程

选题阶段分开记录关键词候选和同账号异常表现，用同平台、同类型与相近观察时间的数据比较。缺数据就保留缺失；基线、样本量和绝对表现一起看，不因一条高值修改整个策略。

写作阶段先列任务书、来源和待核事实，再做平台改写与编辑复审。实测结论必须能回到原始记录。学习记录注明平台、内容类型和适用情境，单次修改先作弱参考，重复观察或明确确认后再提升权重。每天只选择一个可验证的改进，继续使用已有复盘记录。

视觉阶段先判断读者需要看什么：软件步骤和结果用真实截图或证据卡；概念封面、关系解释才考虑生成图。归藏等卡片工具与其他版式工具按单篇需要选一个。宝玉的配图与封面子技能、Ian的解释图保留为未安装候选；不因选中视觉模块就启用同仓库的发布模块。

视频阶段先完成脚本，再明确每个镜头承担的解释任务。提示词方法可以跨工具参考，但模型参数、素材引用与时长限制必须按实际供应商核验。保留一个主合成引擎；数学或结构动画有明确需求时再试制独立素材。字幕、字体边界、音画时长、剪点和最终听检分别验收。剪映草稿交接与最终MP4导出是不同交付物。

发布阶段复用现有任务身份与回执。请求结果不明时先查询原任务；保存草稿、上传成功、排队和已公开分别记录。研究文档中的发布指令不构成使用者授权，也不能覆盖平台访问限制。长文章、扩展同步或新浏览器后端只在真实缺口出现后评估。

可使用 [内容审稿记录模板](../templates/content_review.example.json)，将字段合并到现有记录，不另建发布台账。

## 25项目录

|目标|选择|接入位置|
|---|---|---|
|[yanhua1010/self-media-content-workflow](https://github.com/yanhua1010/self-media-content-workflow)|方法借鉴|复盘与交付|
|[SpaceZephyr/creator-buddy](https://github.com/SpaceZephyr/creator-buddy)|暂缓|采集能力缺口评估|
|[otter1101/blogger-distiller](https://github.com/otter1101/blogger-distiller)|方法借鉴|对标研究|
|[fxyadela/write-then-publish](https://github.com/fxyadela/write-then-publish)|排除商业接入|无|
|[xintu1314/content-boom-monitor](https://github.com/xintu1314/content-boom-monitor)|方法借鉴|热点筛选|
|[Xiangyu-CAS/xiaohongshu-ops-skill](https://github.com/Xiangyu-CAS/xiaohongshu-ops-skill)|暂缓|发布前检查|
|[imraywang/wewrite](https://github.com/imraywang/wewrite)|方法借鉴|审稿与每日学习|
|[wechatsync/Wechatsync](https://github.com/wechatsync/Wechatsync)|暂缓|未来草稿同步备选|
|[xaiwind/x-article-publisher](https://github.com/xaiwind/x-article-publisher)|暂缓|未来长文章备选|
|[JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills)|候选采用|概念封面与配图|
|[op7418/guizang-social-card-skill](https://github.com/op7418/guizang-social-card-skill)|沿用已有|证据图卡|
|[adrianpunk/Punk-Skill](https://github.com/adrianpunk/Punk-Skill)|许可暂缓|取得授权后再评估封面|
|[helloianneo/ian-xiaohei-illustrations](https://github.com/helloianneo/ian-xiaohei-illustrations)|候选采用|长文解释图|
|[mcncarl/yichen-skills](https://github.com/mcncarl/yichen-skills)|许可暂缓|取得授权后再评估|
|[imlewc/video-to-subtitle-summary-skill](https://github.com/imlewc/video-to-subtitle-summary-skill)|方法借鉴|素材整理|
|[xueyuanhuang/seedance-prompt-skill](https://github.com/xueyuanhuang/seedance-prompt-skill)|方法借鉴|内容驱动分镜|
|[Vincentwei1021/video-talkcraft](https://github.com/Vincentwei1021/video-talkcraft)|许可暂缓|取得授权后再评估|
|[oil-oil/video-publisher-skill](https://github.com/oil-oil/video-publisher-skill)|方法借鉴|发布恢复与去重|
|[mcncarl/jianying-headless](https://github.com/mcncarl/jianying-headless)|许可暂缓|取得授权后再评估|
|[heygen-com/hyperframes](https://github.com/heygen-com/hyperframes)|沿用已有|主视频合成|
|[remotion-dev/remotion](https://github.com/remotion-dev/remotion)|暂缓|特殊React动画备选|
|[affaan-m/everything-claude-code/skills/remotion-video-creation/SKILL.md](https://github.com/affaan-m/ECC/blob/main/skills/remotion-video-creation/SKILL.md)|方法借鉴|视频质量检查|
|[affaan-m/everything-claude-code/skills/manim-video/SKILL.md](https://github.com/affaan-m/ECC/blob/main/skills/manim-video/SKILL.md)|方法借鉴|技术概念分镜|
|[browser-use/video-use](https://github.com/browser-use/video-use)|方法借鉴|口播剪辑与检查|
|[luoluoluo22/jianying-editor-skill](https://github.com/luoluoluo22/jianying-editor-skill)|沿用已有|可编辑草稿交接|

## 许可与接入前检查

MIT、Apache、AGPL、GPL及自定义许可不可互换。AGPL/GPL不等于禁止商业使用，但复制、修改、分发或特定网络服务可能涉及相应义务；工具代码、生成素材、字体和第三方图片应分别判断。当前非商业限制涉及 Punk、Yichen、video-talkcraft、jianying-headless 与 write-then-publish 等目标，具体以目录所列来源的许可为准。缺LICENSE或仅有README声明的目标，先补核授权文本。

安装前固定已审查版本，检查执行脚本、更新行为、网络请求、凭据保存与文件覆盖范围；不要自动执行上游的升级、整套安装或付费调用。先用最小独立样例验证输入输出、中文排版、画幅、素材权利和恢复行为，再决定是否进入常规链。需要登录态、云转写或图像服务的模块，还应明确上传哪些材料和如何记录费用。

从 [技能来源](skills.md) 返回依赖目录；组合后的生产路径见 [运营流程](operations.md)、[内容节奏](content-cadence.md) 与 [AI视频制作](ai-video-workflow.md)。这些文档提供通用方法，不继承任何账号授权或实际运行状态。
