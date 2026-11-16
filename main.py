import asyncio
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from time import monotonic

import aiohttp
from astrbot.api import AstrBotConfig
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star


@dataclass(frozen=True)
class Service:
    name: str
    url: str
    response_fields: tuple[str, ...] = ()
    auth_rejections: tuple[int, ...] = ()


SERVICES = (
    Service(
        "Microsoft Login",
        "https://login.live.com/oauth20_token.srf",
        ("error",),
        auth_rejections=(400,),
    ),
    Service(
        "Xbox Auth",
        "https://user.auth.xboxlive.com/user/authenticate",
        auth_rejections=(400, 401),
    ),
    Service(
        "Xbox XSTS",
        "https://xsts.auth.xboxlive.com/xsts/authorize",
        auth_rejections=(400, 401),
    ),
    Service(
        "Minecraft API",
        "https://api.minecraftservices.com/publickeys",
        ("profilePropertyKeys",),
    ),
    Service(
        "Session Server",
        "https://sessionserver.mojang.com/session/minecraft/profile/069a79f444e94726a5befca90e38aaf5",
        ("id", "name", "properties"),
    ),
    Service(
        "Mojang API",
        "https://api.mojang.com/users/profiles/minecraft/Notch",
        ("id", "name"),
    ),
)


async def probe(session: aiohttp.ClientSession, service: Service) -> str:
    start = monotonic()
    if service.name == "Microsoft Login":
        request = session.post(
            service.url,
            data={"grant_type": "authorization_code"},
            allow_redirects=False,
        )
    elif service.auth_rejections:
        request = session.post(service.url, json={}, allow_redirects=False)
    else:
        request = session.get(service.url, allow_redirects=False)

    http_status = None
    try:
        async with request as response:
            http_status = response.status
            auth_rejected = http_status in service.auth_rejections
            if auth_rejected or (http_status == 200 and not service.auth_rejections):
                status = "🟢" if auth_rejected else "🟢"
                if service.response_fields:
                    payload = await response.json()
                    if not isinstance(payload, dict) or not all(
                        payload.get(field) for field in service.response_fields
                    ):
                        status = "🟠 响应内容异常"
            elif http_status == 429:
                status = "🟠 请求受限"
            elif 500 <= http_status <= 599:
                status = "🔴 服务端错误"
            else:
                status = "🟠 返回异常"
    except (aiohttp.ContentTypeError, ValueError):
        status = "🟠 响应内容异常"
    except asyncio.TimeoutError:
        status = "🔴 探测超时"
    except aiohttp.ClientSSLError:
        status = "🔴 TLS 连接失败"
    except aiohttp.ClientConnectionError:
        status = "🔴 连接失败"
    except aiohttp.ClientError:
        status = "🔴 请求失败"

    details = f"{(monotonic() - start) * 1000:.0f} ms"
    if http_status is not None:
        details = f"HTTP {http_status} · {details}"
    return f"{status} {service.name}（{details}）"


class MicrosoftStatusPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self._timeout_seconds = max(1, config.get("timeout_seconds", 5))
        self._cache_seconds = max(0, config.get("cache_seconds", 30))
        self._cache: tuple[float, str] | None = None
        self._query_task: asyncio.Task[str] | None = None

    @filter.command("msstatus", alias={"微软状态"})
    async def msstatus(self, event: AstrMessageEvent):
        """查询 Microsoft、Xbox 和 Minecraft 的服务状态。"""
        if (
            self._cache is not None
            and monotonic() - self._cache[0] < self._cache_seconds
        ):
            message = self._cache[1]
        else:
            if self._query_task is None or self._query_task.done():
                self._query_task = asyncio.create_task(self._check_services())
            message = await asyncio.shield(self._query_task)
        yield event.plain_result(message)

    async def _check_services(self) -> str:
        timeout = aiohttp.ClientTimeout(
            total=self._timeout_seconds,
            ceil_threshold=self._timeout_seconds + 1,
        )
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            statuses = await asyncio.gather(*(probe(session, service) for service in SERVICES))
        checked_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
        message = "\n".join(
            (
                "Microsoft / Minecraft 服务状态",
                *statuses,
                f"探测时间 {checked_at}",
            )
        )
        self._cache = (monotonic(), message)
        return message

    async def terminate(self):
        if self._query_task is not None and not self._query_task.done():
            self._query_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._query_task
