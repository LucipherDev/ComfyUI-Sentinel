import re
import unicodedata
import html
from aiohttp import web
from bleach import clean


class Sanitizer:
    @staticmethod
    def sanitize_input(value):
        """Sanitize user input of various types to prevent security risks."""
        if isinstance(value, str):
            value = value.strip()
            value = unicodedata.normalize("NFC", value)
            value = html.escape(value)
            value = value.replace("\r", "").replace("\n", "")
            value = re.sub(r"([;'\-()<>`=])", r"\\\1", value)
            value = re.sub(r"[;&|`]", "", value)
            value = clean(value, tags=[], attributes=[], protocols=[])

            xss_patterns = [
                r"<script.*?>.*?</script>",
                r"javascript:",
                r"vbscript:",
                r"data:text/html",
                r"data:image",
            ]
            for pattern in xss_patterns:
                value = re.sub(pattern, "", value, flags=re.IGNORECASE)

        elif isinstance(value, (int, float)):
            return value

        elif isinstance(value, (list, dict)):
            return (
                [Sanitizer.sanitize_input(item) for item in value]
                if isinstance(value, list)
                else {key: Sanitizer.sanitize_input(val) for key, val in value.items()}
            )

        return value

    def create_sanitizer_middleware(self) -> web.middleware:
        """Create middleware to sanitize all request inputs."""

        @web.middleware
        async def sanitizer_middleware(request: web.Request, handler) -> web.Response:
            """Middleware to sanitize all request inputs."""
            if request.can_read_body:
                try:
                    data = await request.post()
                    sanitized_data = {
                        key: self.sanitize_input(value) for key, value in data.items()
                    }
                    request["_sanitized_data"] = sanitized_data
                except Exception:
                    pass

            if request.query:
                sanitized_query = {
                    key: self.sanitize_input(value)
                    for key, value in request.query.items()
                }
                request["_sanitized_query"] = sanitized_query

            return await handler(request)

        return sanitizer_middleware
