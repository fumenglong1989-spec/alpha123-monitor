# 当前选择

已采用官方备用站 + 免费公开 GitHub 标准 Ubuntu runner。连续4次云端普通浏览器读取200，详见 DEPLOYMENT.md。以下主站阻塞和替代方案记录保留作为历史诊断。

# 合规免费运行方案评估（2026-10-10）

## 已验证的阻塞

本地 Windows：普通 HTTP 首页 200，API 403；普通 Chromium 页面及其 API 请求均 200。
GitHub Ubuntu：普通 HTTP 首页/API 都 403，响应有 `server: cloudflare`、`cf-mitigated: challenge`；普通 Chromium 首页同样 403，没有加载空投数据。

这能确认 GitHub 云端正常请求触发了 Cloudflare 挑战，不能仅凭此证明具体是 IP、地理位置、浏览器特征或网站的哪条规则。GitHub 官方说明 Ubuntu runner 使用 Azure IP 范围，共享 IP 的信誉可能受其他用户影响。

不解验证码、不使用 stealth、代理轮换或验证 cookie 注入；不通过换出口去规避已知挑战。没有网站明确许可前，不把其他云平台包装成已解决的方案。

来源：https://docs.github.com/en/actions/reference/runners/github-hosted-runners
来源：https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-githubs-ip-addresses

## 方案比较

| 方案 | 免费条件 | 对当前项目的适用性 |
|---|---|---|
| Public GitHub + 标准 Ubuntu | runner 免费，已部署 | 最少改动；需要网站允许自动读取的数据入口或正常访问授权，当前阻塞 |
| Cloudflare Workers Free，直接读取公开 API | 每天 100,000 请求；每日 288 次远低于请求额度 | 仅在网站提供允许正常访问的 API 后可评估；Python Playwright 项目不能原样运行，需适配运行时、持久化与邮件连接；当前无验证通过的 Cloudflare 访问结果 |
| Cloudflare Browser Run Free | 每天 10 分钟浏览器时长 | 288 次/天平均最多约 2.08 秒/次，还须留出重试余量；不能保证当前浏览器工作量符合，且仍可能被挑战，不采用付费升级 |
| Render Free web service | 免费实例但空闲会休眠 | 官方禁止免费服务向 25/465/587 端口发送流量，无法使用本项目的163 SMTP；不采用 |
| Render Cron | 最低每月 1 美元 | 不符合零费用要求，不创建 |
| 自托管 runner | GitHub 不收 runner 分钟费 | 需要已有全天在线设备或经核实的免费云资源；用户 Windows 关机目标使本地电脑方案不适用，没有现成免费云账户权限或可用资源可供验收 |

来源：https://developers.cloudflare.com/workers/platform/limits/
来源：https://developers.cloudflare.com/browser-run/limits/
来源：https://render.com/docs/free
来源：https://render.com/docs/cronjobs

## 当前决定

邮件已修复并通过真实双收件人验收。定时 workflow 为 disabled_manually，仓库变量 MONITOR_ENABLED=false，形成双重关闭；手动 Deployment Validation 工作流没有 schedule。

网站限制无法由仓库代码修复。下一项必要条件是网站提供允许正常自动读取的入口/授权，或者获得一个符合网站规则且实测通过的免费运行环境。当前没有证据支持“免费换个平台就能工作”，因此没有注册新服务、迁移 SMTP Secrets、启用付费服务或冒充完成监控上线。
