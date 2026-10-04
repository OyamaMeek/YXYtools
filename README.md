# 易校园个人校园卡余额监测

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

首次成功查询建立基准，之后只有净余额变化才产生 Telegram 通知。消息先显示“余额”，下一行显示“变动”，正数表示增加、负数表示减少；包含上次余额及观察间隔。余额不变不产生新通知。接口只反映净变化，无法还原每笔交易或将差额断言为消费、充值。

`monitor.py` 每次执行完退出，北京时间 `[07:30, 23:00)` 内允许查询和发送。有效观察值与待发消息先原子写入，再提交、推送到独立 `state` 分支；保存成功后才发送。Telegram 返回明确成功并核对接收目标后，保存消息标识。网络失败保留待发消息，有界退避重试；每次执行最多发送或重试 3 次。限流遵守 retry_after，较长等待留给后续执行。凭证或权限错误停止重复发送，修复后可手动允许重试。连续 3 次查询失败仅产生一次故障通知，保留有效余额；成功恢复后继续比较。

发送结果不明确，或发送成功后保存结果失败，下次执行可能重复发送。已有失败待发消息会继续重试，即使本次余额不变。历史发送确认保留最近 128 项，更早记录可在 state 分支提交历史中查看。

本地运行需先重新检出最新状态，避免与 Actions 并发操作同一状态分支：

```bash
git clone --single-branch --branch state https://github.com/OyamaMeek/YXYtools.git work/state-current
python3 monitor.py --config work/client-private.json --state-dir work/state-current --env-file .env
```

不要同时手动运行本地监测与 Actions。状态读取失败、账户或接收目标变更、分支不同、未保存改动、远端不同步时明确失败，不当作首次初始化。Git 推送失败后重新检出最新 state 到新的忽略目录，继续处理远端保存的待发消息；不要用旧 checkout 覆盖远端。

工作流 `Campus card balance monitor` 使用 Python 3.12，只有标准库运行依赖。定时计划为北京时间 07:30、08:00 至 22:30 每半小时，共 31 次，使用 UTC cron `30 23 * * *` 和 `0,30 0-14 * * *` 表达。所有手动和定时执行共用 concurrency 组，不取消执行中的任务。GitHub 可能延迟或丢弃定时事件；启动及每次业务请求前均检查实际时间，夜间跳过。自动触发须通过 Actions 中的 `schedule` 事件验证，手动运行成功只能验证手动流程。[GitHub 定时规则](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)

Actions 使用 Secrets `YXY_LOGIN_CONFIG`（本地登录配置的完整 JSON）、`TELEGRAM_BOT_TOKEN` 和 `TELEGRAM_CHAT_ID`；这些值已加密上传，不进入仓库文件或日志。公开仓库的 state 分支按已确认的可见性保存余额、观察时间、待发消息和确认标识；不保存 token、uuToken、账户或接收 Chat ID。

在 [Actions 页面](https://github.com/OyamaMeek/YXYtools/actions) 选择工作流，再选择 Run workflow。默认不重试已阻塞的权限错误；修复接收权限后勾选 retry_blocked。修改 Bot Token 时更新同名 Secret，程序会允许新凭证重新尝试；更换接收目标属于状态身份变更，需单独迁移状态。手动执行还会调用 getMe 验证 Telegram 网络，不发送测试消息。

暂停监测：在工作流菜单选择 Disable workflow；恢复时选择 Enable workflow。夜间及停用期间的净变化会在下一次成功查询时与上次有效基准比较。会话失效后更新 YXY_LOGIN_CONFIG 中的 token 与 session_secret；后者为新登录的 uuToken，不能把固定 sign 放入配置。

检查命令：`python3 -m unittest discover -s tests -v`。检查使用真实本地 Git 远端和 JSON 状态文件，覆盖变化、零余额、故障去重、重新检出后的待发恢复、确认保存、推送失败及时间边界。Telegram 真实连接测试已送达并经用户确认；Actions 实际运行结果另见开发日志。[Telegram 发送响应](https://core.telegram.org/bots/api#sendmessage)
