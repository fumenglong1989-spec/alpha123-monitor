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

公开仓库、标准 ubuntu-latest，不启用收费资源。Cron `2-57/5 * * * *`，GitHub调度可能延迟或丢弃，公开仓库60天无活动可能停用；不保证严格5分钟送达或永久无需维护。

最终启用与真实 schedule 证据将在正式初始化通过后追加。
