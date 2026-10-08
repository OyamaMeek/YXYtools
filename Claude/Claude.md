# 易校园校园卡余额变动 Telegram 推送：执行记录

更新时间：2026-10-08，Asia/Shanghai。

## 已确认范围

- 杭州电子科技大学信息工程学院，本人账户、一张指定校园卡、一个 Telegram 聊天，只读查询余额及交易明细。
- Python 标准库单次执行；GitHub Actions 每半小时计划运行一次，北京时间允许窗口为 `[07:30, 次日 01:00)`。
- 首次成功查询只建立基准。之后余额不变时不生成新通知；增加、减少和零余额按 Decimal 比较。
- 通知显示“余额”，下一行显示带正负号的“变动”，附上次余额和观察间隔。余额变化时通过 cardQuerynoPage 查询项目、金额和交易/到账时间，按观察间隔内的到账时间筛选；明细可能因延迟到账与净变动不一致，不从差额推断项目。
- 独立 `state` 分支持久保存有效余额、待发消息及回执。仓库为公开仓库，用户已确认状态遵循其可见性；状态不保存凭证。
- 夜间不查询、不推送；次日恢复后比较最新余额，可能包含夜间净变化。Actions 可能排队或延迟，不能保证准点送达。

## 已完成的功能切片

| 阶段 | 实现与验证 |
| --- | --- |
| 样本分析 | 分析展开的 Payload：易校园 7.8.5、arm64、cryptid=0；没有原始 IPA，未验证压缩包完整性。报告见 `docs/2026-10-04_reverse-yxy-report.md` |
| 鉴权及查询 | 按会话关联两份 HTTP Catcher 抓包，恢复游客和登录签名。完整密码登录响应 uuToken 为签名密钥，新时间戳真实查询成功，指定卡片余额与同期 App 的 10.17 元一致 |
| 变化及状态 | 首次基准、无变化、增加、减少、零余额、故障去重、实际 Git 保存失败和下一次待发恢复检查通过。状态读取失败明确终止，不清空已有记录 |
| Telegram | 实际连接测试已成功送达，用户确认收到。后续监测余额不变时未新增消息；手动 Actions 的 Telegram 检查使用只读 getMe |
| Actions | Secrets 已加密配置，工作流已提交至 main。三次托管运行成功，后续观察时间推进，基准恢复且没有新增待发或确认消息 |
| 时间限制 | 共用时段判定，07:29 禁止、07:30 允许、23:00 允许、00:59 允许、01:00 禁止。每次余额查询、通知和手动 Telegram 请求发起前再次检查实际时间 |
| 扣费明细与延长窗口 | 新抓包和实时明细查询确认热水、餐厅及补助圈存记录；11 项测试通过。窗口延至次日 01:00，35 个执行时点及全部 1440 分钟的 Actions/客户端判定一致 |

## 实际实现与失败处理

| 文件 | 职责 |
| --- | --- |
| `client.py` | 签名、只读余额及按日期交易明细请求、严格响应校验、共用北京时间窗口 |
| `monitor.py` | 单次流程、Decimal 变化比较、故障事件去重、Git 状态、Telegram 发送和重试 |
| `tools/run_monitor.py` | 读取 Actions 私有配置，不覆盖既有配置，退出时仅删除本次临时文件 |
| `tools/check_telegram.py` | 手动运行的只读 Bot 身份及网络检查 |
| `tests/test_monitor.py` | 5 项实际状态、真实隔离 Git、配置保护及边界检查 |
| `tests/test_transactions.py`、`tests/fixtures/transactions.json` | 6 项明细解析、通知、长消息、跨日和失败保留基准检查；真实抓包样本仅替换流水号 |
| `.github/workflows/monitor.yml` | 定时及手动入口、Secrets 注入、Python 3.12、共用 concurrency 和 state checkout |
| `README.md` | 配置、手动运行、停止、恢复、凭证更新和验证命令 |

新观察与对应待发消息先原子保存并普通推送到远端 state，成功后才发送。Telegram 返回 `ok=true`、正确聊天及有效 message_id 后保存回执。推送失败立即终止；Telegram 失败保留消息，有界退避或遵守 retry_after；永久配置错误暂停该队列，可更新配置或手动选择重试。余额未变化时，既有失败待发消息仍可继续重试。

查询失败不更新有效基准，不把错误转换为零余额；连续失败按事件发送一次告警，成功后清除故障状态。返回成功但保存回执失败、或发送结果不明确时，后续重试可能重复，不能保证每条消息恰好送达一次。

工作流每天计划执行 35 次：07:36、08:06 至次日 00:36，每半小时一次。全部监测入口使用同一 concurrency 组，不取消正在执行的任务；每次执行退出，有界网络超时。登录 JSON、Bot Token、Chat ID 使用 Actions Secrets。本地抓包、凭证、`.env`、运行数据位于忽略目录；既有已跟踪 Payload 保持原样。

## 验证命令与证据

```bash
python3 -m unittest discover -s tests -v
python3 tools/verify_client.py --config work/client-private.json --login-evidence work/login-private.json --success-evidence work/new-query-private.json --failure-evidence work/replay-private.json --expected-yuan 10.17
python3 tools/verify_balance_capture.py yxy_app/2026_10_04__11_40_30 --expected-yuan 10.17
PYTHONPYCACHEPREFIX=work/__pycache__ python3 -m py_compile client.py monitor.py tools/run_monitor.py tools/check_telegram.py tests/test_monitor.py
```

客户端检查需要本地已有私有配置和证据；历史分析文件清理后不自动重建。单元检查使用实际 JSON 和隔离 Git 远端，不用伪造接口成功替代网络验收。

- [首次 GitHub 实际运行](https://github.com/OyamaMeek/YXYtools/actions/runs/37179080148)：查询、状态、Telegram 网络检查通过。
- [第二次 GitHub 实际运行](https://github.com/OyamaMeek/YXYtools/actions/runs/37179174868)：再次查询成功，远端观察时间推进，余额不变且没有新消息。
- [最终代码 GitHub 实际运行](https://github.com/OyamaMeek/YXYtools/actions/runs/37179863052)：cd0fea1 的请求时间限制、真实查询、状态恢复和 Telegram 网络检查通过；余额相同，没有新通知。
- [明细通知实际测试](https://github.com/OyamaMeek/YXYtools/actions/runs/37803865949)：2026-10-08 23:49 手动正式运行全部成功，净减少 3.10 元，新增一次发送确认且待发为空；用户提供的通知全文与真实余额和明细重建文本逐字一致。没有发起充值或消费来制造变化。
- token 有效期和自动续期未验证；失效后本人正常重新登录，更新 token 与完整登录响应 uuToken，并重新保存 Secrets。
- 时间边界已覆盖 07:29、07:30、22:59、23:00、00:59、01:00；尚未完成整夜运行观察、每类网络故障或真实登录失效恢复的现场验证。
- 2026-10-08 23:38 真实余额查询成功，余额 120.98 元；明细接口返回四条记录，与用户截图中的项目和金额一致。23:49 已通过正式通知流程验证；扩展时段的 schedule 运行尚未验证。

## 官方参考

- Telegram：[`sendMessage` 与结构化响应](https://core.telegram.org/bots/api#sendmessage)。
- Python：[`decimal` 金额运算](https://docs.python.org/3/library/decimal.html)。
- GitHub Actions：[定时执行、时区与调度限制](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)、[Secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)。
