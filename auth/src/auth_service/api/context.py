import ipaddress

from fastapi import Request

from auth_service.application.contracts import RequestContext
from auth_service.config import get_settings


def _is_trusted_proxy(ip_address: str | None) -> bool:
    """Check whether an address belongs to a configured proxy network."""
    if ip_address is None:
        return False
    try:
        client_address = ipaddress.ip_address(ip_address)
    except ValueError:
        return False
    for proxy in get_settings().trusted_proxy_ips:
        try:
            if client_address in ipaddress.ip_network(proxy, strict=False):
                return True
        except ValueError:
            continue
    return False


def request_metadata(request: Request) -> tuple[str | None, str | None]:
    """Extract client IP and user agent from a request."""
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    if _is_trusted_proxy(ip_address):
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            candidate = forwarded_for.split(",", maxsplit=1)[0].strip()
            try:
                ip_address = str(ipaddress.ip_address(candidate))
            except ValueError:
                pass
    return user_agent, ip_address


def request_context(request: Request) -> RequestContext:
    """Build audit context from the current request."""
    user_agent, ip_address = request_metadata(request)
    return RequestContext(
        request_id=getattr(request.state, "request_id", None),
        ip_address=ip_address,
        user_agent=user_agent,
    )
