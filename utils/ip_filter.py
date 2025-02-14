import os
import hashlib
import ipaddress

from aiohttp import web
from pathlib import Path


def get_ip(request: web.Request) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.headers.get("X-Real-IP")

    if not ip:
        ip = request.remote

    try:
        ip = str(ipaddress.ip_address(ip))
    except ValueError:
        ip = ""

    return ip


class IPFilter:
    def __init__(self, whitelist_file: str | Path, blacklist_file: str | Path):
        self.whitelist_file = whitelist_file
        self.blacklist_file = blacklist_file

        self._whitelist_hash = None
        self._blacklist_hash = None

        self.whitelist = []
        self.blacklist = []

        self.load_filter_list()

    @staticmethod
    def calculate_file_hash(filter_file) -> str:
        """Calculate the SHA256 hash of the filter IP list file."""
        if os.path.exists(filter_file):
            with open(filter_file, "rb") as f:
                file_data = f.read()
                return hashlib.sha256(file_data).hexdigest()
        return ""

    def load_filter_list(self) -> tuple[dict, dict]:
        """Load whitelist and blacklist IP lists from files."""

        def load_ip_list(
            file_path: str | Path, current_hash: str, hash_attribute: str
        ) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
            ip_list = []
            new_hash = self.calculate_file_hash(file_path)
            if new_hash != current_hash:
                if os.path.exists(file_path):
                    with open(file_path, "r") as f:
                        for line in f:
                            ip = line.strip()
                            if ip:
                                try:
                                    ip_list.append(ipaddress.ip_address(ip))
                                except ValueError:
                                    continue
                    setattr(self, hash_attribute, new_hash)

            else:
                return getattr(self, hash_attribute.split("_")[0])

            return ip_list

        self.whitelist = load_ip_list(
            self.whitelist_file, self._whitelist_hash, "_whitelist_hash"
        )
        self.blacklist = load_ip_list(
            self.blacklist_file, self._blacklist_hash, "_blacklist_hash"
        )

        return self.whitelist, self.blacklist

    def is_allowed(self, ip: str) -> bool:
        """
        Checks if the given IP address is allowed based on the whitelist and blacklist.
        - If the whitelist is not empty, the IP must be in the whitelist to be allowed.
        - If the whitelist is empty, the IP is denied if it is in the blacklist.
        - If the whitelist is empty and IP is not in the blacklist, it is allowed.
        """
        self.load_filter_list()

        try:
            ip = ipaddress.ip_address(ip)
        except:
            return False

        if self.whitelist:
            if ip in self.whitelist:
                return True

            return False

        if ip in self.blacklist:
            return False

        return True

    def add_to_blacklist(self, ip: str) -> None:
        """Add a given IP to the blacklist"""
        try:
            ip = ipaddress.ip_address(ip)
        except ValueError:
            return
        if ip not in self.blacklist:
            self.blacklist.append(ip)

            with open(self.blacklist_file, "a") as file:
                if file.tell() > 0:
                    file.seek(file.tell() - 1)
                    if file.read(1) != "\n":
                        file.write("\n")

                file.write(str(ip) + "\n")

    def create_ip_filter_middleware(self) -> web.middleware:
        """Create the middleware for managing blacklisted and whitelisted ip."""

        @web.middleware
        async def ip_filter_middleware(request: web.Request, handler) -> web.Response:
            ip = get_ip(request)

            if not self.is_allowed(ip):
                return await handle_access_denied(
                    request,
                    "Access denied: IP is either not whitelisted or is blacklisted.",
                )

            return await handler(request)

        async def handle_access_denied(
            request: web.Request, message: str
        ) -> web.Response:
            """Handle denied access cases."""
            accept_header = request.headers.get("Accept", "")
            if "text/html" in accept_header:
                return web.HTTPForbidden(reason=message)
            else:
                return web.json_response({"error": message}, status=403)

        return ip_filter_middleware
