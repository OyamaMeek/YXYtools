# 当前进度

- 已确认个人只读用途；目标学校：杭州电子科技大学信息工程学院。
- 已分析版本 7.8.5 arm64 主程序，cryptid=0；定位校园卡路径及 sign 请求头。
- 已关联抓包会话 546，成功解码 Brotli，确认实际 getMultiCardMoney 接口及一张卡。
- 原始本人请求真实重放成功，余额与同期 App 一致；用户确认金额单位为元。
- 完整密码登录抓包 `2026_10_04__12_07_02` 已解析；登录签名与实际捕获 sign 逐字节一致。
- 已恢复会话密钥：密码登录响应 uuToken 写入 GlobalUtil.sessionSecret，并与 token 一起保存到 Keychain。
- 新 nt、新签名、最新本人登录凭证的真实查询成功；余额 10.17 元、卡片与原抓包相同。客户端检查和实际 CLI 查询均通过。
- 当前仅用已有登录会话；token 有效期和自动续期未验证。人工重新登录后须更新 token 和 uuToken。
- 用户已确认首次建立基准、净余额变化通知及独立 state 分支。
- 已按用户要求创建项目根目录 `.env`，包含空的 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID，等待填写实际值。按阶段规划暂停依赖真实推送验收的工作流配置；Telegram 与 Actions 尚未实现或验证。
- 原始分析证据在先前工作区 `work/yxy-balance/evidence`，当前不恢复或修改样本。
