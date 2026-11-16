# AstrBot Microsoft 服务状态

发送 `/msstatus` 或 `/微软状态`，机器人会在当前会话回复 Microsoft Login、Xbox Auth、Xbox XSTS、Minecraft API、Session Server 和 Mojang API 的探测结果、HTTP 状态码与耗时。

## 安装

在 AstrBot WebUI 的插件管理中上传插件 ZIP。也可以将源码目录复制到 `data/plugins/astrbot_plugin_ms_status/`，在 AstrBot 的 Python 环境里安装 `requirements.txt` 中的依赖，然后重新加载插件。

## 插件配置

| 设置 | 默认值 | 用途 |
| --- | --- | --- |
| 单项探测超时 | 5 秒 | 六项并行探测，每项独立计时。 |
| 查询结果缓存 | 30 秒 | 多个会话共用结果。设为 0 后，每次新查询都会探测，同时发起的查询共用一轮请求。 |

## 探测结果

Microsoft Login、Xbox Auth 和 Xbox XSTS 使用无凭据请求。Microsoft Login 返回 HTTP 400 且包含 OAuth 错误字段时，机器人会标为「接口有响应」。Xbox Auth 和 Xbox XSTS 的预期拒绝状态为 HTTP 400 或 401。完整的登录流程需要实际账号和有效令牌。

Minecraft API、Session Server 和 Mojang API 分别查询公开密钥、玩家会话档案和玩家名称档案，并检查返回内容。探测结果反映 AstrBot 所在网络到这些接口的表现。连接失败或超时也可能来自本地网络或代理。机器人使用服务器时间显示探测时间，耗时包含建立连接及接收所需响应的时间。

- [AstrBot 插件开发文档](https://docs.astrbot.app/dev/star/guides/simple.html)
- [Minecraft 登录流程](https://mojang-api-docs.gapple.pw/authentication/msa)
- [Mojang API 文档](https://minecraft.wiki/w/Mojang_API)
