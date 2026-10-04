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
