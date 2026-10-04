# 注意事项

- 实际规划路径为 `Claude/Claude.md`；已有样本为展开的 Payload，无原始 IPA。
- 真实余额请求没有 Cookie；token 在表单中，sign 在请求头中。新 nt 不能复用旧 sign。
- HTTP Catcher 导出中并发请求交错，必须按会话标识关联响应，不能取相邻 HTTP 200。
- 不输出、提交原始抓包、请求凭证或个人账户标识。
- 现有 Payload 已被 Git 跟踪；忽略规则不会移除已有跟踪，不擅自删除样本。
- 协议 platform 固定为捕获的 YUNMA_APP；不能从 iOS 操作系统名称推断该值。
- 取位函数从字符串末尾向前计算；签名使用 ymId 倒数第二、第三位，不能读为正向索引。
- 静默登录可能不返回 uuToken；不能以 keyMap 为空判断无法恢复签名。完整登录响应 uuToken 是已验证的会话密钥。
