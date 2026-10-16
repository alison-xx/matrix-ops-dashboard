# X官方API接入（尚需实际账号验收）

仅使用公开官方API，通过OAuth1.0a管理自己的账号。复制config/x-api.example.json为config/x-api.json，首次保持enabled=false及预算0。将你自己的OAuth凭据保存为config/x-api-secrets.json并chmod 600，字段为consumer_key、consumer_secret、access_token、access_token_secret；不要提交或同步此文件。schedule的x发布位需自己配置account_id和handle。

适配器支持status/check/add/submit/inbox。安装requirements-ops.txt，审核后将最终稿哈希写入同stem.review.json（status=pass，sha256，checks含human-writing/humanizer-zh/content-compliance-checker）。post.json需id、day、time、account、kind=text、body、title、column、score≥7；审核方法见自己的编辑规范。x_api.py add ID HH:MM post.json将新稿加入ops.py dispatch，不重复导入原生定时。

开启前核实官方应用读写权限、实际账户身份及额度，配置本地日/周期预算和官方账期上限。首次真实发帖需有价值内容，GET回读作者与正文，不能仅凭离线测试宣称接通。POST超时记uncertain，不自动重试；先查本人作品。未获平台许可不能启用AI回复机器人；脚本没有自动点赞、私信或陌生人批量回复。inbox内容仅存本机state/x-api-private（0700/0600）。

本地计费预占为保守估计，实际费用以[官方定价](https://docs.x.com/x-api/getting-started/pricing)为准。[发帖接口](https://docs.x.com/x-api/posts/create-post)，[自动化规则](https://help.x.com/en/rules-and-policies/x-automation)。
