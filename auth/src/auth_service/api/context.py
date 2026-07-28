import ipaddress

from fastapi import Request

from auth_service.application.contracts import RequestContext
from auth_service.config import get_settings


def request_metadata(request: Request) -> tuple[str | None, str | None]:
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    if ip_address in get_settings().trusted_proxy_ips:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            candidate = forwarded_for.split(",", maxsplit=1)[0].strip()
            try:
                ip_address = str(ipaddress.ip_address(candidate))
            except ValueError:
                pass
    return user_agent, ip_address


def request_context(request: Request) -> RequestContext:
    user_agent, ip_address = request_metadata(request)
    return RequestContext(
        request_id=getattr(request.state, "request_id", None),
        ip_address=ip_address,
        user_agent=user_agent,
    )
