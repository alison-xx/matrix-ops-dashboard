---
name: platform-content-review
description: Review final text and media wording for each target platform, with contextual risk adjudication and a versioned review record.
---

# 逐平台发布前用词复核

读取 `运营手册/发布前违禁词检查.md`。本技能编排检查，不内置或复制第三方技能词库。

1. 输入目标平台、内容类型、最终标题/正文/简介/话题/首评，以及封面、配图、字幕和口播的完整文本与版本。
2. 如安装了 content-compliance-checker，读取其 SKILL.md，按候选词表找出位置、原句和风险类别。未安装则明确标记缺失并先安装或进行有来源的人工复核，不声称执行过该技能。
3. 结合语境复核：客观提及、新闻引述、否定句与广告承诺分开判断；不得机械把词表命中写成平台违规。微博、知乎、B站没有该技能专用词库，应明示并补充当前平台官方规则。
4. 有问题就保持事实与限定词改写；不以谐音、符号规避。改图或旁白后重新生成并复检相应素材。
5. 在 review.md 逐平台记录版本、范围、候选、处理依据、复检和结论。无法读取素材或仍有待核实项，不写通过。
6. 该步骤通过后仍需执行 lint 与平台状态核验。ops.py 目前没有全素材审核记录的自动拦截。

输出只表示本次检查发现了什么，不保证审核结果，不编造法规或平台规则出处。
