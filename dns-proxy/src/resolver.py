"""DNS resolver with AI domain monitoring.

Forwards DNS queries to upstream resolver while logging
queries to monitored AI platform domains.
"""

import asyncio
import struct
from datetime import datetime, timezone

import httpx
import structlog

from src.config import (
    AUTH_TOKEN,
    CAPTURE_API_URL,
    GROUP_ID,
    LISTEN_HOST,
    LISTEN_PORT,
    MEMBER_ID,
    MONITORED_DOMAINS,
    UPSTREAM_DNS,
    UPSTREAM_PORT,
)

logger = structlog.get_logger()


class DNSProxy:
    """Simple DNS proxy that monitors AI platform queries."""

    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=5.0)

    async def handle_query(self, data: bytes, addr: tuple) -> bytes:
        """Forward DNS query to upstream and log if monitored."""
        # Extract query name from DNS packet
        domain = self._extract_domain(data)

        if domain:
            # Check if this is a monitored AI domain
            platform = self._match_platform(domain)
            if platform and GROUP_ID and MEMBER_ID:
                asyncio.create_task(self._report_query(domain, platform, addr[0]))

        # Forward to upstream DNS
        return await self._forward_query(data)

    def _extract_domain(self, data: bytes) -> str | None:
        """Extract the queried domain name from a DNS packet."""
        try:
            # Skip DNS header (12 bytes)
            offset = 12
            labels = []
            while offset < len(data):
                length = data[offset]
                if length == 0:
                    break
                offset += 1
                labels.append(data[offset:offset + length].decode("ascii"))
                offset += length
            return ".".join(labels).lower() if labels else None
        except Exception:
            return None

    def _match_platform(self, domain: str) -> str | None:
        """Check if domain matches a monitored AI platform."""
        for monitored_domain, platform in MONITORED_DOMAINS.items():
            if domain == monitored_domain or domain.endswith("." + monitored_domain):
                return platform
        return None

    async def _forward_query(self, data: bytes) -> bytes:
        """Forward DNS query to upstream resolver via TCP."""
        try:
            reader, writer = await asyncio.open_connection(UPSTREAM_DNS, UPSTREAM_PORT)
            # TCP DNS: prepend 2-byte length
            writer.write(struct.pack("!H", len(data)) + data)
            await writer.drain()

            # Read response length
            length_data = await reader.readexactly(2)
            response_length = struct.unpack("!H", length_data)[0]

            # Read response
            response = await reader.readexactly(response_length)
            writer.close()
            await writer.wait_closed()
            return response
        except Exception as e:
            logger.error("dns_forward_failed", error=str(e))
            return data  # Return original on failure

    async def _report_query(self, domain: str, platform: str, client_ip: str) -> None:
        """Report a monitored DNS query to the capture gateway."""
        try:
            event = {
                "group_id": GROUP_ID,
                "member_id": MEMBER_ID,
                "platform": platform,
                "session_id": f"dns-{domain}-{datetime.now(timezone.utc).isoformat()}",
                "event_type": "session_start",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {"domain": domain, "client_ip": client_ip},
            }
            headers = {}
            if AUTH_TOKEN:
                headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

            await self.http_client.post(CAPTURE_API_URL, json=event, headers=headers)
            logger.info("dns_query_reported", domain=domain, platform=platform)
        except Exception as e:
            logger.warning("dns_report_failed", error=str(e), domain=domain)

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()


class UDPProtocol(asyncio.DatagramProtocol):
    """UDP protocol handler for DNS proxy."""

    def __init__(self, proxy: DNSProxy):
        self.proxy = proxy
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple):
        asyncio.create_task(self._handle(data, addr))

    async def _handle(self, data: bytes, addr: tuple):
        try:
            response = await self.proxy.handle_query(data, addr)
            self.transport.sendto(response, addr)
        except Exception as e:
            logger.error("dns_handle_error", error=str(e))


async def main():
    """Start the DNS proxy server."""
    proxy = DNSProxy()
    logger.info("dns_proxy_starting", host=LISTEN_HOST, port=LISTEN_PORT)

    loop = asyncio.get_event_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPProtocol(proxy),
        local_addr=(LISTEN_HOST, LISTEN_PORT),
    )

    logger.info("dns_proxy_started", host=LISTEN_HOST, port=LISTEN_PORT)

    try:
        await asyncio.Event().wait()  # Run forever
    finally:
        transport.close()
        await proxy.close()


if __name__ == "__main__":
    asyncio.run(main())
