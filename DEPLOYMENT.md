# 部署验收记录（2026-10-10）

正式来源：官方备用站 https://zh1.alpha123.net/ ，实际 API `/api/data`。普通 Playwright Chromium，无挑战绕过。主站 https://alpha123.uk/zh/ 留作参考，其 403 是访问失败，不是今日空列表。

连续四次标准 GitHub Ubuntu 读取：首页/API 均 HTTP 200，响应 application/json，上游2个历史项目，今日0项，解析成功：
- https://github.com/fumenglong1989-spec/alpha123-monitor/actions/runs/38036637712
- https://github.com/fumenglong1989-spec/alpha123-monitor/actions/runs/38036725020
- https://github.com/fumenglong1989-spec/alpha123-monitor/actions/runs/38036788556
- https://github.com/fumenglong1989-spec/alpha123-monitor/actions/runs/38036846196

四个独立实例使用隔离 monitor-acceptance 分支：首次新增生成2份邮件；再次读取相同项目仍2份；新增第二项目共4份；积分变化共6份。每批两个收件人分别记录，pending为空，运行ID不同。只生成纯文本/HTML邮件，无 SMTP 调用，无 SMTP Secrets，真实虚构通知发送量0。生产状态为独立 monitor-state 分支。

24项自动化测试在本地及上述每次云端均通过，包括失败闭锁、逐收件人重试、北京时间跨日与重启去重。当前真实今日为空，真实非空页面仍需未来持续观察，不能声称已现场验收非空表格。

现有 smtp.163.com:465 和 SMTP_USER/SMTP_PASSWORD Secrets 保留，未覆盖。此前真实邮件测试163服务器接受两个收件人，用户确认两个QQ邮箱实际收到，日志 https://github.com/fumenglong1989-spec/alpha123-monitor/actions/runs/38035345829 。该旧任务整体失败是主站访问403，不是邮件失败。

公开仓库、标准 ubuntu-latest，不启用收费资源。Cron `3/5 * * * *`，GitHub调度可能延迟或丢弃，公开仓库60天无活动可能停用；不保证严格5分钟送达或永久无需维护。

## 最终免费部署验收（2026-10-12，北京时间）

已使用 Cloudflare Workers Free，Cron `*/5 * * * *`，仅触发现有公开GitHub仓库的标准Ubuntu任务，没有新增收费资源。MONITOR_ENABLED=true、SCHEDULER_SOURCE=cloudflare。原生 `3/5 * * * *` 未修改，作为可选备用，当前原生自动任务按条件跳过。

GitHub原生调度截至本次审计已有9条schedule记录，全部因监控开关或来源选择而跳过。早先零记录未发现工作流配置错误；GitHub内部调度延迟的确切原因无法从仓库API判断。Workers的Fetch TypeError已通过请求兼容处理修复，Token权限已由用户确认更新，并核实仅限alpha123-monitor、Actions读写、Metadata只读。没有读取、保存或输出Token内容。

真实只读云端probe https://github.com/fumenglong1989-spec/alpha123-monitor/actions/runs/38194052108 成功，首页/API均200，JSON正常，今日0。

真实Workers自动Cron证据（非人工触发）：
- 10:01:04.701：eventType=scheduled，Cron=*/5 * * * *，scheduled=2026-10-12T02:00:20.000Z，GitHub返回200/run_id=38194139569。该任务因验收前MONITOR_ENABLED=false正常跳过。
- 10:05:38.697：eventType=scheduled，scheduled=2026-10-12T02:05:20.000Z，GitHub返回200/run_id=38194437058。https://github.com/fumenglong1989-spec/alpha123-monitor/actions/runs/38194437058 成功完成：source=https://zh1.alpha123.net/，api_status=200，content_type=application/json，today_count=0；新增/更新0，pending0；monitor-state GET/PUT均200，并保留旧日期。
- Workers对应日志：https://dash.cloudflare.com/2e6e86df3de4a864ea71eefa9da7af7a/workers/services/view/alpha123-dispatch-scheduler/production/observability/events （需账户登录）。

明确标注的人工重复槽位验收：https://github.com/fumenglong1989-spec/alpha123-monitor/actions/runs/38194554199 ，复用上一自动事件时间；独立Ubuntu运行记录duplicate_skipped、original_run=38194437058，没有再次读取空投网站或调用SMTP，生产状态逐字段不变。该验收不是自动调度证据。原有4个独立实例的模拟新增/去重/再次新增/更新邮件测试继续保留；没有发送虚构空投通知。

现有163 SMTP Secrets与monitor.py/notifier.py/config.py保持原样。两个QQ收件人此前都已实际收件验收。本次真实今日为空，没有发送空投邮件；未来真实新增的实际收件仍应按邮箱收件记录判断，不能把工作流成功视为邮件已读或已收件。

28项Python测试（含新调度去重与逐收件人维护提醒）和9项Worker测试通过。Token实际到期日期2027-01-08，GitHub变量DISPATCH_TOKEN_EXPIRES_AT已设置；在到期前14/7/1天各发送一次真实维护提醒，按收件人分别持久化与重试。到期前必须自行续期并更新Cloudflare加密Secret和到期日期变量。若SMTP同时故障，邮件提醒不能保证收件，需关注GitHub失败日志。

停止监控：设置MONITOR_ENABLED=false或移除Workers Cron，保留monitor-state。不要同时手动启用两个来源；SCHEDULER_SOURCE选cloudflare或github其中一个。免费调度和GitHub排队可能延迟，不保证严格每5分钟完成。

