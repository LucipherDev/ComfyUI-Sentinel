import jwt
from aiohttp import web
from datetime import datetime, timedelta, timezone

from .users_db import UsersDB
from .access_control import AccessControl
from .logger import Logger


class JWTAuth:
    def __init__(
        self,
        users_db: UsersDB,
        access_control: AccessControl,
        logger: Logger,
        secret_key: str,
        expire_minutes: int = 12 * 60,
        algorithm: str = "HS256",
    ):
        self.users_db = users_db
        self.access_control = access_control
        self.logger = logger

        self.expire_minutes = expire_minutes
        self.algorithm = algorithm

        self.__secret_key = secret_key

    @staticmethod
    def get_token_from_request(request: web.Request) -> str:
        """Extract token from request headers or cookies."""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[len("Bearer ") :]
        return request.cookies.get("jwt_token")

    def create_access_token(self, data: dict, expire_minutes=None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if not expire_minutes:
            expire_minutes = self.expire_minutes
        expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, self.__secret_key, algorithm=self.algorithm)

    def decode_access_token(self, token: str) -> dict:
        """Decode a JWT access token."""
        return jwt.decode(token, self.__secret_key, algorithms=[self.algorithm])

    def create_jwt_middleware(
        self,
        public: tuple = (),
        public_prefixes: tuple = (),
        public_suffixes: tuple = (),
    ) -> web.middleware:
        """Create middleware for JWT authentication."""

        @web.middleware
        async def jwt_middleware(request: web.Request, handler) -> web.Response:
            """Middleware to handle JWT authentication."""
            if (
                request.path in public
                or request.path.startswith(public_prefixes)
                or request.path.endswith(public_suffixes)
            ):
                return await handler(request)

            token = self.get_token_from_request(request)

            if not token:
                return await handle_unauthorized_access(request, "/login")

            try:
                user = self.decode_access_token(token)
                user_id = user.get("id")
                username = user.get("username")
                if not user_id == self.users_db.get_user(username)[0]:
                    raise ValueError(
                        f"User with username: {username} is not in the database"
                    )

                request["user_id"] = user_id
                request["user"] = username

                set_fallback = request.path in ["/api/prompt"]
                self.access_control.set_current_user_id(user_id, set_fallback)

            except jwt.ExpiredSignatureError:
                return await handle_unauthorized_access(
                    request, "/logout", message="Token has expired"
                )
            except jwt.DecodeError:
                return await handle_unauthorized_access(
                    request, "/logout", message="Token is invalid"
                )
            except Exception as e:
                self.logger.error(f"Unexpected error during token decoding: {e}")
                return await handle_unauthorized_access(
                    request, "/logout", message="Unexpected error"
                )

            return await handler(request)

        async def handle_unauthorized_access(
            request: web.Request,
            redirect_path: str,
            message: str = "Authentication required",
        ) -> web.Response:
            """Handle unauthorized access cases."""
            accept_header = request.headers.get("Accept", "")
            if "text/html" in accept_header:
                return web.HTTPFound(redirect_path)
            else:
                return web.json_response({"error": message}, status=401)

        return jwt_middleware
