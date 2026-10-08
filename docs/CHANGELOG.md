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
  - GitHub 托管运行器两次实际运行通过，任务 37179080148、37179174868；后次观察时间推进，余额相同，没有新增待发或确认消息。真实消费产生的变化尚未发生，自动续期未验证。
- **涉及文件**：
  - monitor.py、tests/test_monitor.py、tools/run_monitor.py、tools/check_telegram.py
  - .github/workflows/monitor.yml、README.md、memory/plan.md、memory/progress.md、memory/verify.md
- **Git 提交**：`f673d26 feat: monitor campus card balance changes with durable Telegram delivery`；本条实际哈希补记由后续提交保存。

---

## [2026-10-04 13:14] 全部业务请求入口检查北京时间

- **需求/问题描述**：
  > 按已确认规划，夜间不查询、不发送，独立客户端也遵守运行时间窗口。
- **实际实现的功能与改动**：
  - 查询客户端与监测共用时间窗口判定，在余额、发送及手动 Telegram 检查发起请求前再次检查时间。
  - 执行期间进入夜间时停止新请求，不将其记录为余额查询故障。
  - 5 项检查、真实本人余额查询及 Python 编译通过；仍返回 10.17 元。
- **涉及文件**：
  - client.py、monitor.py、tests/test_monitor.py、tools/check_telegram.py
- **Git 提交**：`cd0fea1 fix: enforce Beijing time window at request boundaries`；实际哈希补记由后续文档提交保存。

---

## [2026-10-04 13:28] 最终 Actions 验收与交付记录

- **需求/问题描述**：
  > 删除通知中的“真实查询”，下一行显示变动；余额未改变时不推送，完成已授权的定时监测。
- **实际实现的功能与改动**：
  - 最终代码 cd0fea1 的 GitHub 任务 [37179863052](https://github.com/OyamaMeek/YXYtools/actions/runs/37179863052) 成功，查询、远端状态恢复及只读 Telegram 网络检查通过。
  - 与前次远端状态比较：观察时间推进，余额仍为 10.17 元，pending 为空、sent 未增加，没有新增推送。
  - 最终本地 5 项检查及 Python 编译通过；更新执行记录、逆向报告和持久记录，保存可见对话。
  - 真实变化后的现场接收、整夜运行、会话有效期及自动续期未验证，交付文档明确这些范围。
- **涉及文件**：
  - Claude/Claude.md、docs/2026-10-04_reverse-yxy-report.md、docs/CHANGELOG.md
  - memory/agents.md、memory/progress.md、memory/verify.md、memory/gotchas.md
  - context/2026/10/04/13-28-14/对话.md
- **Git 提交**：功能 `f673d26`、时间限制 `cd0fea1` 已推送。用户明确授权公开推送后，验收文档 `c180283 docs: record deployed monitor and Actions verification` 和补记 `4509bc8 docs: record delivery commit and publication approval block` 均已推送；远端 main 实际哈希与本地 4509bc8 一致。

## [2026-10-04 13:33] 授权推送交付记录

- **需求/问题描述**：
  > 用户明确授权推送包含学校名称、余额和监测说明的交付记录。
- **实际实现的功能与改动**：
  - 普通推送 origin/main 成功，通过 git ls-remote 核对远端提交为 4509bc8，与本地一致。
  - 保存本次可见授权及推送进度消息。没有修改功能代码，没有重复运行业务测试。
- **涉及文件**：
  - docs/CHANGELOG.md、memory/progress.md、context/2026/10/04/13-33-39/对话.md
- **Git 提交**：交付记录 c180283、4509bc8 已推送；本条补记随文档提交保存。

---

## [2026-10-04 14:11] 核对并推送 Actions 部署

- **需求/问题描述**：
  > 用户询问 GitHub Actions 部署及机密信息存放位置，随后要求代理推送到 GitHub。
- **实际实现的功能与改动**：
  - 核对现有 monitor 工作流、Secrets 引用及 state 分支；部署代码已在 origin/main。
  - 执行普通 git push，远端返回 Everything up-to-date；此前 git ls-remote 确认远端 main 为 08d9fa285ab013bb6ee0ea4f2adab086c15b43ac，与本地一致。
  - 保存部署说明与本次可见对话；没有修改功能代码，没有重新执行测试或业务查询，没有读取或上传凭证值。
  - 不提交与本任务无关的 .DS_Store 修改。普通 push 的本地远端引用更新受到沙箱限制，后续 Git 写操作使用宿主审批机制。
- **涉及文件**：
  - docs/CHANGELOG.md、memory/progress.md、context/2026/10/04/14-11-43/对话.md
- **Git 提交**：`5a2e5d6 docs: record Actions deployment push verification` 已普通推送至 origin/main；git ls-remote 核对远端哈希与本地一致。本条实际哈希由后续文档提交补记。

---

## [2026-10-04 17:07] 排查定时运行缺失并重新启用工作流

- **需求/问题描述**：
  > 用户报告校园卡监测没有自动执行，Actions 页面仅有手动运行。
- **实际实现的功能与改动**：
  - GitHub API 确认 3 次运行均为 workflow_dispatch，schedule 运行数量为 0；仓库未停用或归档，默认分支 main，Actions enabled=true，工作流 active。
  - 核对远端 YAML 与当前 GitHub 官方文档，Asia/Shanghai 时区及 cron 配置有效；GitHub 状态 API 没有未解决事故。尚无法确定 GitHub 内部未触发的具体原因。
  - 通过 GitHub API 禁用再启用工作流，实际状态依次为 disabled_manually、active。重新启用后 schedule 仍为 0，自动执行恢复未确认；下一计划时间为北京时间 17:30。
  - 没有修改业务代码、定时配置、Secrets 或 state；没有额外发送消息或手动触发。仅更新验证范围与持久记录，没有重复运行业务测试。
- **涉及文件**：
  - memory/progress.md、memory/verify.md、memory/gotchas.md、docs/CHANGELOG.md
- **Git 提交**：`7e58493 docs: record scheduled workflow investigation and reactivation` 已普通推送至 origin/main，git ls-remote 核对远端与本地一致；实际哈希由后续文档提交补记。

---

## [2026-10-04 17:43] 使用等价 UTC 定时计划并诊断自动触发

- **需求/问题描述**：
  > 用户报告重新启用工作流后 17:30 仍未自动执行。
- **实际实现的功能与改动**：
  - GitHub API 确认只有 3 次手动运行，没有新定时事件。
  - monitor.yml 使用等价 UTC cron，逐项核对北京时间 07:30 至 22:30 的 31 个时间点；保留每次请求前的北京时间窗口校验。
  - 暂时部署无权限、无凭证、无业务请求的定时诊断工作流，计划在北京时间 17:48 和 17:53 输出事件和时间，完成诊断后删除。
  - 两份工作流 YAML 解析、UTC 日期与时点换算、现有 5 项测试及 git diff --check 通过。自动执行恢复仍待 GitHub schedule 事件验证，尚未认定时区字段为原因。
- **涉及文件**：
  - .github/workflows/monitor.yml、.github/workflows/schedule-probe.yml
  - memory/plan.md、memory/verify.md、docs/CHANGELOG.md
- **Git 提交**：`c15e430 fix: use equivalent UTC monitor schedule and probe automatic triggers` 已普通推送至 origin/main，GitHub API 核对 main 哈希一致；实际哈希由后续文档提交补记。

---

## [2026-10-04 18:03] 记录 UTC 诊断结果并清理临时工作流

- **需求/问题描述**：
  > 排查 17:30 未触发；用户明确选择继续只使用 GitHub 定时触发。
- **实际实现的功能与改动**：
  - 核对 17:48、17:53 临时 UTC 诊断和 18:00 正式监测；截至 18:02:45，均没有 schedule 事件，总运行仍为 3 次手动，远端有效观察仍为 13:26:43。
  - 通过 API 禁用临时诊断，确认 disabled_manually 后删除工作流；保留每天北京时间 07:30 至 22:30 的 31 个 UTC 时间点。
  - 更新 README、计划、进度及验收记录。短期没有事件不能排除延迟到达；自动执行未恢复，未认定时区字段为原因，未将手动查询作为恢复证据。
  - YAML 解析、31 个时点换算及 5 项测试在 c15e430 提交前通过；本次仅清理诊断和更新文档，执行 git diff --check，无业务代码改动，不重复运行业务测试。
  - 原始排查快照仅保存在忽略的 work/schedule-investigation.json；没有新增调度服务或凭证存放位置。
- **涉及文件**：
  - .github/workflows/schedule-probe.yml（删除）、README.md
  - memory/plan.md、memory/progress.md、memory/verify.md、memory/gotchas.md、docs/CHANGELOG.md
- **Git 提交**：`5ef3250 docs: record UTC scheduling evidence and remove temporary probe` 已普通推送至 origin/main，git ls-remote 核对远端与本地一致；实际哈希由后续文档提交补记。18:04:27 的 API 复核仅剩正式工作流 active，定时事件仍为 0，状态观察未推进。

---

## [2026-10-05 10:27] 迁移 Telegram 群组接收目标并恢复余额查询

- **需求/问题描述**：
  > 用户更换 Telegram 对话后，自动监测因 ValueError 终止，要求修复。
- **实际实现的功能与改动**：
  - 真实状态校验重现接收目标身份不符；用户授权后迁移 state identity，余额基准、观察时间、故障状态及历史发送记录全部保留，迁移时 pending 为空。
  - 同步本地 .env 与 TELEGRAM_CHAT_ID Secret；没有修改 Bot Token、登录配置或业务代码，保留严格身份校验。
  - 5 项 unittest 和 git diff --check 通过；本人只读余额查询成功。
  - 用户确认的群组目标正式手动运行 [37255430805](https://github.com/OyamaMeek/YXYtools/actions/runs/37255430805) 全部成功，远端观察时间推进至 10:26:59；余额未变，pending 为 0，sent 未增加，没有新增通知。
  - 群组 getChat 返回 200，ID 匹配；getChatMember 确认 @YXYtools_bot 为 administrator。没有额外发送测试消息，真实余额变化的群组接收尚未发生。
  - 已确认两次 schedule 事件；尚无迁移后的定时成功证据，不将本次手动运行表述为定时稳定性验收。
- **涉及文件**：
  - state 分支的 state.json；忽略的本地 .env；Actions TELEGRAM_CHAT_ID Secret
  - memory/plan.md、memory/progress.md、memory/verify.md、memory/gotchas.md、docs/CHANGELOG.md
- **Git 提交**：最终群组 state 迁移 `d8eb546 chore: persist monitor state` 已普通推送，原目标恢复点为 02a74d5；交付记录 `77888cc docs: record Telegram group migration and monitoring recovery` 已普通推送至 origin/main，远端哈希核对一致。本条实际哈希由后续文档提交补记。

---

## [2026-10-06 12:17] 调整半小时监测至每小时 06、36 分

- **需求/问题描述**：
  > 用户要求在 06 分执行，以错开 GitHub 整点调度。
- **实际实现的功能与改动**：
  - UTC cron 调整为 `36 23 * * *`、`6,36 0-14 * * *`，对应北京时间 07:36 至 22:36，每半小时一次，共 31 次；保留 [07:30, 23:00) 查询与通知窗口。
  - README、计划、进度与验收记录已同步；没有修改业务代码、Secrets 或 state，也没有手动触发业务请求。
  - 新计划断言先因原 cron 失败，调整后 YAML 解析及同一断言通过；完整时点换算、30 分钟间隔、窗口边界、现有 5 项 unittest 和 git diff --check 均通过。
  - 实际调度改善仍待新配置的 schedule 事件验证，错开分钟不能保证准时执行。
- **涉及文件**：
  - .github/workflows/monitor.yml、README.md
  - memory/plan.md、memory/progress.md、memory/verify.md、docs/CHANGELOG.md
- **Git 提交**：`0f38b70 fix: offset monitor schedule to minutes 06 and 36` 已普通推送至 origin/main，git ls-remote 核对远端哈希与本地一致；本条实际哈希由后续文档提交保存。

---

## [2026-10-08 13:59] 排查校园卡监测运行失败

- **需求/问题描述**：
  > 用户报告 GitHub Actions 突然运行失败。
- **实际实现的功能与改动**：
  - 运行 37734752752 第 2 次尝试的日志确认余额查询失败；前置测试与状态恢复成功。
  - 本地两次真实只读查询均返回 success=true、statusCode=0，但卡片列表为空，客户端拒绝读取指定卡片；本地身份与远端状态匹配。
  - 有效余额基准保留，故障计数为 2，待发队列为空。没有修改业务代码、凭证或状态，没有发送额外通知。
  - 查询尚未恢复，需结合 App 卡片及余额查询结果继续判断原因。本次仅保存排查记录，未额外运行测试套件。
- **涉及文件**：
  - memory/progress.md、memory/verify.md、docs/CHANGELOG.md
- **Git 提交**：待提交。

---
