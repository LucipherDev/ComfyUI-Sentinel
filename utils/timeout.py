from typing import Optional
from aiohttp import web
from datetime import datetime, timezone, timedelta

from .ip_filter import IPFilter, get_ip

class Timeout:
    def __init__(self, ip_filter: IPFilter, blacklist_after_attempts: int = 0):
        self.ip_filter = ip_filter
        self.blacklist_after_attempts = blacklist_after_attempts

        self._failed_attempts_ip = {}
        self._timeout_end_time_ip = {}

    def get_failed_attempts(self, ip: str) -> int:
        """Get the number of failed attempts for a given IP."""
        return self._failed_attempts_ip.get(ip, 0)

    def add_failed_attempt(self, ip: str) -> None:
        """Add a failed attempt for a given IP and set timeout or blacklist IP if necessary."""
        whitelist, _ = self.ip_filter.load_filter_list()

        if ip in whitelist:
            return

        self._failed_attempts_ip[ip] = self._failed_attempts_ip.get(ip, 0) + 1
        failed_attempts = self._failed_attempts_ip[ip]

        if not self.blacklist_after_attempts == 0:
            if failed_attempts >= self.blacklist_after_attempts:
                self.ip_filter.add_to_blacklist(ip)

        timeout_duration = 0
        if failed_attempts >= 9:
            timeout_duration = 300
        elif failed_attempts >= 6:
            timeout_duration = 90
        elif failed_attempts >= 3:
            timeout_duration = 60

        if timeout_duration > 0:
            self._timeout_end_time_ip[ip] = datetime.now(timezone.utc) + timedelta(
                seconds=timeout_duration
            )

    def remove_failed_attempts(self, ip: str) -> None:
        """Remove failed attempts and timeout for a given IP."""
        self._failed_attempts_ip.pop(ip, None)
        self._timeout_end_time_ip.pop(ip, None)

    def get_timeout_end_time(self, ip: str) -> Optional[datetime]:
        """Get the timeout end time for a given IP."""
        return self._timeout_end_time_ip.get(ip)

    def check_is_timed_out(self, ip: str) -> tuple[bool, int, int]:
        """Check if a given IP is currently timed out."""
        timeout_end_time = self.get_timeout_end_time(ip)

        if timeout_end_time and datetime.now(timezone.utc) < timeout_end_time:
            remaining_seconds = round(
                (timeout_end_time - datetime.now(timezone.utc)).total_seconds()
            )
            return True, self.get_failed_attempts(ip), remaining_seconds

        return False, self.get_failed_attempts(ip), 0

    def create_time_out_middleware(self, limited: tuple = ()) -> web.middleware:
        """Create middleware for handling timeouts."""

        @web.middleware
        async def time_out_middleware(request: web.Request, handler) -> web.Response:
            """Middleware to handle request timeouts."""
            if request.path in limited and request.method == "POST":
                is_timed_out, failed_attempts, remaining_seconds = (
                    self.check_is_timed_out(get_ip(request))
                )

                if is_timed_out:
                    minutes, seconds = divmod(int(remaining_seconds), 60)

                    if minutes > 0:
                        remaining_time = f"{minutes} minute{'s' if minutes > 1 else ''} and {seconds} second{'s' if seconds > 1 else ''}"
                    else:
                        remaining_time = f"{seconds} second{'s' if seconds > 1 else ''}"

                    return web.json_response(
                        {
                            "error": f"Too many failed attempts. Please wait {remaining_time}",
                            "failed_attempts": failed_attempts,
                            "remaining_seconds": remaining_seconds,
                        },
                        status=403,
                    )

            return await handler(request)

        return time_out_middleware
