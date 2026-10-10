# Alpha123 今日空投监控

独立 Python 项目，正式来源为官方备用站 https://zh1.alpha123.net/ ，主站 https://alpha123.uk/zh/ 保留作参考及邮件链接。每次运行检查一次。仅读取 `#today-airdrops`，排除预告和历史。北京时间判断日期；首次汇总、新项目、积分/数量/时间变化分别提醒，两个固定收件人分别发送 UTF-8 纯文本和 HTML 邮件。

## 真实网站验证（2026-10-10）

正常浏览器页面内联 JavaScript 请求 `/api/data?fresh=${forceFresh ? '1' : '0'}`，实际捕获 URL 为 `https://alpha123.uk/api/data?fresh=1`，HTTP 200，响应包含 `airdrops` 数组（2 个历史项目，样本 CLO 日期 2026-10-09）；今日表格正确排除这两项。渲染使用 `id/token/name/points/amount/date/beijing_time/phase`。普通 Python HTTP 请求页面与该接口均得到 403，因此不采用直接 HTTP 数据采集。普通 Playwright Chromium（不使用 stealth、不注入 cookie、不绕过验证码）成功加载该 API 并解析今日表格。2026-10-10 15:00 北京时间实际 `--probe` 返回 0 个项目，与浏览器“暂无数据”一致。

正式监控采用备用站的普通 Playwright 浏览器，捕获实际 `/api/data` 响应；主站 403 不代表今日无数据，不作为空结果或降级依据。默认始终采用浏览器，不猜测接口，不从其他栏目补数据。接口成功、JSON 结构正常、今日渲染对象存在、表头正确、数量一致才接受结果。空表格且没有明确“暂无数据”、HTTP 403、加载失败均停止通知。网络失败最多尝试 3 次，间隔 5/10 秒。未来网站结构变化需维护；当前没有真实非空项目，因此非空解析经过模拟验证，尚未实际非空验收。

## 免费方案与限制

使用**公开 GitHub 仓库 + 标准 ubuntu-latest runner**。工作流对私有仓库直接跳过，避免意外分钟收费；不使用收费大型 runner、artifact 或 Actions cache。邮件凭据只存 Secrets。公开状态分支只存项目、检测时间及收件人哈希，不存密码。代码中的固定收件邮箱也会公开。

2026-10-10 核实 GitHub 官方规则：公开仓库标准 runner 免费；私有 GitHub Free 每月 2,000 分钟，Pro 3,000 分钟。每次 job 向上取整到整分钟，30 天每 5 分钟 8,640 次至少 8,640 分钟，私有免费额度不足。不要改成私有仓库或大型 runner；在账户 Billing → Budgets and alerts 对 Actions 设零预算并启用超额停止（若账户界面提供），不要增加付费缓存/存储。

- 计费：https://docs.github.com/en/billing/concepts/product-billing/github-actions
- 分钟取整：https://docs.github.com/en/actions/how-tos/monitor-workflows/view-job-execution-time
- 定时限制：https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- 禁用规则：https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows

cron 为每小时 02、07…57 分，避开整点拥挤。GitHub schedule 可能延迟，严重时丢弃，并非严格 5 分钟 SLA；只在默认分支运行。公共仓库连续 60 天无活动会自动停用定时工作流。不要假设机器人状态提交能永久规避该规则：建议每月人工检查 Actions 并提交一次 README 维护记录，停用后重新启用。零费用方案不能保证永久无人维护或 5 分钟必达。

## 本地安装和验证

需要 Python 3.12+。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
python -m unittest discover -s tests -v
python monitor.py --probe
```

`--probe` 不发送、不修改状态。`.env.example` 仅作参考，程序不自动读取 .env。终端环境变量配置后 `python monitor.py` 执行一次完整监控。长期运行使用下面 GitHub 部署，不需要 Windows 开机。

## GitHub 部署（需要你登录账户操作）

1. GitHub → New repository，名称 `alpha123-monitor`，选择 **Public**。不要选择付费服务。将本目录内容上传，保留 `.github/workflows/monitor.yml`。若网页上传不能保留隐藏目录，使用下面 Git。
2. 在本项目目录执行：

```powershell
git init
git add .
git commit -m "Add Alpha123 monitor"
git branch -M main
git remote add origin https://github.com/YOUR_USER/alpha123-monitor.git
git push -u origin main
```

3. Settings → Secrets and variables → Actions → New repository secret，添加 `SMTP_USER`（发送163邮箱完整地址）和 `SMTP_PASSWORD`（SMTP 授权码）。不要发给聊天助手、不要提交到代码。
4. Settings → Actions → General 确认允许 Actions。工作流申请 `contents: write`，用于写 `monitor-state` 分支。仓库/组织策略和分支规则必须允许该分支写入；主分支可以保护。不要把 `monitor-state` 设为默认分支。
5. Actions → Alpha123 Monitor → Run workflow，先选 `probe`。日志显示真实网站检查成功，且不是 HTTP/解析错误。
6. Run workflow 选择 `test-mail`（bootstrap=false），这是明确的一次真实测试发送；确认两个收件箱/垃圾邮件箱都收到。
7. **仅首次部署** Run workflow 选择 `monitor`，bootstrap=true。自动创建 `monitor-state` 分支及 state.json，若当前有项目会立即通知。后续始终 bootstrap=false。旧状态丢失时不要勾选初始化，应恢复状态，避免重复。
8. 检查后续定时运行成功。已有状态无新项目时不发邮件。有失败收件人会在下一次成功检查中重试；即使今日已空，旧待发队列仍重试。

## 网易163邮箱 SMTP

登录发送邮箱的网易163邮箱网页版，进入设置中的账户或账号安全，找到 POP3/IMAP/SMTP 服务（界面名称可能调整）。开启 SMTP/IMAP 服务，按页面要求完成手机验证，生成第三方客户端授权码。使用授权码作为 SMTP_PASSWORD，不能使用 163邮箱登录密码。将授权码直接填入 GitHub Secret；撤销授权码后更新 Secret 即可轮换。发件服务固定为 SMTP_SSL `smtp.163.com:465`，证书验证始终开启。两个 QQ 地址仅作为收件人。

独立邮件测试：GitHub 手动 `test-mail`，或在自己的终端设置环境变量后运行：

```powershell
$env:SMTP_USER = '你的发送邮箱@163.com'
# 请通过自己的安全方式设置 SMTP_PASSWORD，避免把授权码写入脚本或共享终端历史。
python notifier.py
```

测试不会修改监控去重状态；模拟测试不会发送真实邮件。SMTP 接受不等于最终投递到收件箱，需人工确认首次测试和排查退信。

## 持久化与故障语义

使用 GitHub Contents API 在 `monitor-state/state.json` 保存状态，SHA 乐观并发保护，workflow concurrency 禁止重叠发送。待发队列发送前远端持久化，每个收件人成功后立即写回。任何远端写入失败都会停止继续发送；状态缺失/损坏默认拒绝启动。不能改用 cache/artifact 去重，因为它们可能过期或淘汰。本地原子文件状态适用于单进程测试，本地请勿同时启动多个实例。

SMTP 和状态存储之间无法做分布式事务：如果 SMTP 已接受邮件后进程崩溃、网络返回不确定或 GitHub 状态提交失败，下轮可能重复该封邮件。这是至少一次投递的固有限制，不能声称严格 exactly-once。正常完成的邮件当天不重复，积分/数量/时间变化发送更新；项目识别基于当天的接口 id，id 缺失/重复则保守停止。同名重复行也保守停止，避免错误归并；网站更换 id 会视为新项目。历史去重保留 35 天，待发队列独立保存。

每次运行仍保存状态，日志含检测时间、项目数、新增/更新数、各收件人成功/失败。日志只打印异常类型，不打印 SMTP 登录错误全文、凭据或 HTTP Authorization。测试覆盖 Github API 状态恢复与 SHA 写入；实际 GitHub token 权限及云端网站访问需部署后验证。

## 日志、排查和停止

Actions → Alpha123 Monitor → 某次运行 → Run monitor or explicit test 查看日志。红色运行表示抓取、状态写入或某个收件人失败。网站 403/验证码：停止抓取，等待正常访问恢复，不绕过。邮件错误日志区分 network_connection_failed、tls_handshake_failed、authentication_rejected、server_disconnected、recipient_rejected、smtp_protocol_failed，并记录安全的阶段和响应数字码；不输出服务器错误正文和密码。仅身份认证明确被拒绝时才检查凭据，不将网络或断连判定为授权码错误。写状态失败：检查 contents 权限、monitor-state 分支保护和原始状态文件；不要直接删除状态。若长期没有运行，检查定时 workflow 是否被 60 天规则停用。

停止：Actions → Alpha123 Monitor → 右上菜单 → Disable workflow。保留 monitor-state 便于恢复；再次 Enable workflow 后可继续去重。也可撤销163邮箱 SMTP 授权码。无需购买服务器。

额外关闭开关：Settings → Secrets and variables → Actions → Variables 中 MONITOR_ENABLED 默认为 false。只有网站 probe 和双收件人邮件验收通过后才改为 true 并启用 monitor 工作流。该变量只影响 schedule；Deployment Validation 仅手动运行，没有 schedule。

## 当前交付状态

项目已上传到 https://github.com/fumenglong1989-spec/alpha123-monitor ，Secrets 已设置。发件服务已修正为网易163，SMTP 分别接受两封测试邮件，用户确认两个QQ邮箱均已实际收到。主站云端403已通过切换官方备用站解决：连续4次首页/API200、今日解析成功、跨实例模拟去重验收通过。正式初始化完成，MONITOR_ENABLED=true，定时工作流已启用。实际定时执行证据见 DEPLOYMENT.md；免费方案评估见 FREE_HOSTING.md。Deployment Validation 仅供手动验收，没有 schedule，不会启动监控。

## 跨运行验收

`acceptance.yml` 手动依次选择 phase 1、2、3、4。每个独立实例先真实读取备用站，再在隔离的 `monitor-acceptance` 分支验证新增、去重、再次新增、字段更新，生成 UTF-8 纯文本及 HTML 邮件但不调用 SMTP；该工作流没有 SMTP Secrets。重复阶段会失败，禁止重置生产状态。生产仅使用 `monitor-state` 分支。

停止监控：在 Actions 禁用 Alpha123 Monitor，并将仓库 Actions 变量 `MONITOR_ENABLED` 改成 `false`。密码和授权码仍仅存原有 Secrets，不需重新生成。
