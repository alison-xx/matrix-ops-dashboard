# Public matrix workspace

使用简体中文报告。先读 docs/operations.md、docs/privacy.md 和运营手册/00-必读.md。
看板 demo 使用虚构数据。scripts 中包含会发帖、发邮件、付费和同步的工具；只有在使用者明确授权且配置好自己的集成后执行。公开模板不继承原工作区的授权、账号和定时器。
改动提交前运行 scripts/check_public_tree.py，审查 diff，并执行与变更相称的验证。不要将真实 config、state、days、reports、个人媒体或凭据提交到 Git。
