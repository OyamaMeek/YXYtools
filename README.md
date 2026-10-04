# 易校园个人校园卡余额查询

已支持杭州电子科技大学信息工程学院本人指定卡片的只读查询。Python 标准库即可运行；不需要 Cookie。新时间戳签名及真实余额查询已通过，余额与同期 App 的 10.17 元一致。

```bash
python3 client.py --config work/client-private.json
```

本地已经生成当前本人会话的 `work/client-private.json`，权限为 600，受 `.gitignore` 排除。配置包含 `school_name`、`ym_id`、`device_id`、`token`、`session_secret` 和 `wallet_no`，均为非空字符串。`session_secret` 来自完整密码登录响应的 `data.uuToken`，`token` 来自 `data.token`。学校和设备也从本人登录证据取值；卡片来自实际余额响应，不能猜测或替换其他账号标识。

查询仅访问已验证的 `getMultiCardMoney` 接口，有 20 秒超时，不自动重试或跳转，不执行支付或充值。使用 Decimal 金额，业务失败、字段异常、卡片不符均终止，不生成零余额。配置失效后在本人 App 正常重新登录，重新取得本人 `token` 与 `uuToken` 并更新私有配置；自动续期和 token 有效期尚未验证。

真实证据检查命令如下，会发送一次本人只读余额查询，检查过程不打印凭证：

```bash
python3 tools/verify_client.py --config work/client-private.json --login-evidence work/login-private.json --success-evidence work/new-query-private.json --failure-evidence work/replay-private.json --expected-yuan 10.17
```

上述 `work/` 文件是本地真实分析证据，不进入 Git。`tools/verify_balance_capture.py` 可独立核验第一份原始抓包，需要本机已有的 `/opt/homebrew/bin/brotli`，不属于查询客户端的运行依赖。

首次建立基准、仅通知净余额变化及独立 `state` 分支持久保存已获确认。Telegram 配置、真实送达、监测状态恢复和 GitHub Actions 尚待完成；目前没有创建或启用定时工作流。余额查询只反映观察间隔内的净变化，不能还原具体交易。
