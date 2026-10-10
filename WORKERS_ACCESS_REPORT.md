# 最小访问实测与可行性结论（2026-10-10）

## Workers：已按403停止

使用Cloudflare官方无登录Playground，在真实Workers边缘沙箱运行单次API探测，没有创建账户资源、Cron、KV或付费套餐，也没有复制任何邮件Secrets。

北京时间15:50:46，对已确认的 https://alpha123.uk/api/data?fresh=0 发起普通fetch。

- 上游HTTP：403
- 上游响应类型：text/html; charset=UTF-8
- cf-mitigated：challenge
- parsed：false；没有取得任何可解析空投JSON，绝不能把它视为“今日无项目”
- outcome：STOP_ACCESS_DENIED

收到挑战后停止，没有再次探测上游，没有绕过挑战。源码及结果在 probes/workers_one_shot.js、probes/workers_result.json。截图workers-probe-403.jpg中的200是诊断Worker返回报告的外层状态，不是Alpha123接口的状态；真实上游403记录在报告JSON中。

官方Playground说明：https://developers.cloudflare.com/workers/playground/

Workers Cron可表达每5分钟，即每天288次，远低于免费请求上限100,000/日；但免费额度无法解决接口挑战。因访问测试失败，不进一步部署Cron、存储、邮件或迁移项目。
来源：https://developers.cloudflare.com/workers/platform/limits/

## 官方入口检查

检查主站HTML、内联脚本、页面链接、rel=alternate声明、官方使用手册，以及站内限定API/RSS搜索。

- 真实网页数据接口为/api/data?fresh=0或1，网页脚本直接使用，不是猜测地址。
- 没有在检查范围内找到公开API文档、RSS/Atom订阅入口或明确的自动访问许可说明。网页内部接口不等于有稳定性承诺的公共API；不声称全站绝不存在其他入口。
- 官方使用手册明确写明alpha123.net为备用站。
- 实际访问alpha123.net，页面脚本将其导航到https://zh1.alpha123.net。
- 该备用页面实际脚本与网络响应证实其使用https://zh1.alpha123.net/api/data?fresh=1。
- 网站还提供官方Twitter/Telegram提醒，但不是结构化“今日栏目”API，不能直接替代本监控的精确规则。

官方手册：https://alpha123.uk/manual/zh/icons-reference.html
备用导航入口：https://alpha123.net/
实际备用站：https://zh1.alpha123.net/

## 官方备用站：GitHub免费runner实测通过

最小探测保留普通Playwright Chromium，没有使用stealth、验证cookie、代理、IP轮换或验证码处理。正式monitor没有更换来源，163邮件模块和Secrets均未修改。

北京时间15:55:29，GitHub Public仓库标准ubuntu-latest运行：

- 页面HTTP200，text/html，没有cf-mitigated挑战标记。
- API HTTP200，application/json，没有挑战标记。
- JSON结构验证成功，airdrops有2个项目。
- 今日栏目表头及数量验证成功，today_count=0，today_items=[]。
- 两项为2026-10-09的CLO/BTR，未误判为2026-10-10今日项目。
- 本地主站/备用站的id、token、name、date、time、积分、数量、phase及status逐项一致。

GitHub实际运行：https://github.com/fumenglong1989-spec/alpha123-monitor/actions/runs/38036063398
探测文件：probes/official_backup.py；工作流backup-probe.yml仅手动触发，没有schedule、邮件Secrets或状态写入。

## 明确结论

Workers访问主站的方案未通过，已停止。找到有实际访问证据的免费可行路径：官方备用站 + 现有Public GitHub标准runner + 原有163邮件模块与GitHub状态分支。无需Workers、服务器购买或邮箱配置修改。

这是读取链路验证通过的方案，不是已启用的完整监控。本轮没有切换正式数据来源、初始化状态或开启定时任务；只有一次云端读取成功，尚不足以证明长期稳定和跨运行端到端验收。

正式上线前需要在现有项目中明确配置官方备用来源，验证持久化去重及跨运行邮件逻辑。此前两封真实163测试邮件已由用户确认双邮箱收件，保留该验收。未来官方备用入口的可用性及网页内部接口结构仍需维护。

Public标准GitHub runner免费说明：https://docs.github.com/en/actions/reference/runners/github-hosted-runners
定时monitor仍disabled_manually，MONITOR_ENABLED=false。没有启用付费服务。
