# 开发记录

## [2026-10-04 12:23] 本人校园卡新签名查询客户端

- **需求/问题描述**：
  > 根据 Claude/Claude.md 分析 yxy_app/Payload，并利用本人 HTTP Catcher 抓包完成余额查询和后续监测开发。
- **实际实现的功能与改动**：
  - 关联 HTTP Catcher 请求与响应，确认学校、指定卡片和金额单位。
  - 恢复游客及登录签名，确认完整密码登录 uuToken 为会话密钥；实现仅用标准库的只读查询客户端和私有本地配置。
  - 真实登录签名匹配、原始抓包金额核验、新时间戳实时查询及实际 CLI 均通过，返回 10.17 元；错误响应、卡片不符及非法金额被拒绝，零余额接受检查通过。
  - Python 编译检查通过；缓存定向到被忽略的 work/。私有抓包、原始响应及凭证不提交。
  - 已确认首次建立基准、净余额变化通知和 state 分支。等待 Telegram 配置路径；Telegram、状态恢复及 Actions 尚未实现或验收，自动续期未验证。
- **涉及文件**：
  - client.py、tools/verify_client.py、tools/verify_balance_capture.py
  - README.md、.gitignore、docs/2026-10-04_reverse-yxy-report.md
  - memory/agents.md、memory/plan.md、memory/progress.md、memory/verify.md、memory/gotchas.md
- **Git 提交**：`7ba766e feat: add verified personal campus card balance client`；本条实际哈希补记由后续文档提交保存。

---

## [2026-10-04 12:28] 创建 Telegram 私有配置模板

- **需求/问题描述**：
  > 用户要求创建 .env，以填写 Telegram Bot Token 和 Chat ID。
- **实际实现的功能与改动**：
  - 在项目根目录创建 .env，保留 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID 空值，权限设为 600。
  - 验证变量名称、空值、文件权限及 Git 忽略规则；没有发送 Telegram 请求。
- **涉及文件**：
  - .env（仅本地，不提交）、memory/progress.md、docs/CHANGELOG.md、context/2026/10/04/12-28-10/对话.md
- **Git 提交**：`82af475 docs: record local Telegram environment setup`；实际哈希补记由后续文档提交保存。

---

## [2026-10-04 13:07] 余额变化通知与 Actions 单次监测

- **需求/问题描述**：
  > 用户填好 Telegram 配置并确认实际收到连接测试；要求余额下一行显示变动，未变化不推送，继续完成已确认的定时监测。
- **实际实现的功能与改动**：
  - 实现首次基准、净余额变化、连续故障去重、有界发送重试及北京时间窗口限制。
  - 新观察和待发消息先原子保存并推送到 state 分支，发送成功后保存 message_id；失败不丢弃待发消息。
  - 真实本地查询、Telegram 推送、用户接收及下一次状态恢复通过；未变化没有生成新消息。
  - 5 项单元检查及 Python 编译通过；状态检查使用实际 JSON 文件、隔离 Git 远端和真实失败推送，验证无效 Actions 配置不会覆盖或删除已有私有文件。
  - 登录 JSON、Bot Token、Chat ID 已加密保存为 Actions Secrets；运行无新增依赖。用于本地加密上传的 PyNaCl 只安装在被忽略的 work/，不进入产品或提交。
  - 配置每天北京时间 07:30 至 22:30 共 31 个半小时时间点；全部入口共用 concurrency、不取消正在执行任务，夜间不查询或发送。
  - GitHub 托管运行器的两次运行尚待执行；真实消费产生的余额变化尚未发生，自动续期未验证。
- **涉及文件**：
  - monitor.py、tests/test_monitor.py、tools/run_monitor.py、tools/check_telegram.py
  - .github/workflows/monitor.yml、README.md、memory/plan.md、memory/progress.md、memory/verify.md
- **Git 提交**：待提交。

---
