# XY技能安装参考

来源：https://github.com/xyaz1313/xyskill
快照commit：c9149fb08818cce0dd9bb64b3fa53c9ad9f7465d；快照含49个SKILL.md。
许可：CC BY-NC 4.0，商业授权需联系作者。安装与生产采用分别记录；本公开模板不附带第三方技能原文、知识库或案例，商业用途待适用授权明确。

使用skill-installer按固定commit安装skills目录，并保留仓库根的_shared、knowledge、scripts、tools及LICENSE等依赖。以本机实际目录设置宿主技能入口，检查已有同名目录，不覆盖其他来源。上游安装脚本会涉及多个宿主，执行前逐项审查。校验文件指纹与入口可读性不等于所有业务功能通过验收。

候选方向：xy-ip定位、xy-content-scan内容诊断、xy-course课程结构、xy-ops运营。只有许可和具体任务均适配才采用，不把全部技能强制串联；不自动启用外部API或覆盖现有运营真源。

来源与指纹见../docs/skills-manifest.json。通用计划见IP操盘总计划.md。
