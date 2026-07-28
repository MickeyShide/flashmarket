import ipaddress


def anonymize_ip(ip_address: str | None) -> str | None:
    """Reduce an IP address to a network prefix before persisting it."""
    if ip_address is None:
        return None
    try:
        address = ipaddress.ip_address(ip_address)
    except ValueError:
        return None
    prefix_length = 24 if address.version == 4 else 64
    network = ipaddress.ip_network((address, prefix_length), strict=False)
    return f"{network.network_address}/{prefix_length}"
