from aiohttp import web


def create_https_middleware(match_headers: dict | None) -> web.middleware:
    """
    Create middlware to change scheme of current request when HTTPS headers matched.
    """

    @web.middleware
    async def https_middleware(request: web.Request, handler) -> web.StreamResponse:
        """Change scheme of current request when HTTPS headers matched."""

        matched = any(
            request.headers.get(key) == value for key, value in match_headers.items()
        )

        if matched:
            request = request.clone(scheme="https")

        return await handler(request)

    return https_middleware
