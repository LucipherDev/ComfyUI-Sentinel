import os
import jwt
import uuid
from aiohttp import web

from server import PromptServer

from .utils import *

instance = PromptServer.instance
app = instance.app
routes = instance.routes

logger = Logger(LOG_FILE, LOG_LEVELS)
sanitizer = Sanitizer()
ip_filter = IPFilter(WHITELIST, BLACKLIST)
timeout = Timeout(ip_filter, BLACKLIST_AFTER_ATTEMPTS)
users_db = UsersDB(USERS_FILE)
access_control = AccessControl(users_db, instance)
jwt_auth = JWTAuth(
    users_db, access_control, logger, SECRET_KEY, TOKEN_EXPIRE_MINUTES, TOKEN_ALGORITHM
)


@routes.get("/register")
async def get_register(request: web.Request) -> web.Response:
    with open(os.path.join(HTML_DIR, "register.html"), "r") as f:
        html_content = f.read()

    if not users_db.load_users():
        html_content = html_content.replace("{{ X-Admin-User }}", "true")
    html_content = html_content.replace("{{ X-Admin-User }}", "false")

    return web.Response(body=html_content, content_type="text/html")


@routes.post("/register")
async def post_register(request: web.Request) -> web.Response:
    sanitized_data = request.get("_sanitized_data", {})
    ip = get_ip(request)
    new_user_username = sanitized_data.get("new_user_username")
    new_user_password = sanitized_data.get("new_user_password")
    username = sanitized_data.get("username")
    password = sanitized_data.get("password")

    username_valid, username_invalid_message = validate_username(new_user_username)
    if not username_valid:
        return web.json_response({"error": username_invalid_message}, status=400)

    password_valid, password_invalid_message = validate_password(new_user_password)
    if not password_valid:
        return web.json_response({"error": password_invalid_message}, status=400)

    admin_user = users_db.get_admin_user()
    admin_user_id = None

    if admin_user[0] and (not new_user_username or not new_user_password):
        return web.json_response(
            {"error": "Missing new user registration details"}, status=400
        )

    if admin_user[0]:
        if not username or not password:
            return web.json_response(
                {"error": "Missing admin user authentication details"}, status=400
            )

        admin_user_id = admin_user[0]

        if admin_user_id is not None:
            if not (
                users_db.get_user(username)[0] == admin_user_id
                and users_db.check_username_password(username, password)
            ):
                logger.registration_attempt(
                    ip, username, password, new_user_username, new_user_password
                )
                timeout.add_failed_attempt(ip)
                return web.json_response(
                    {"message": "Invalid username or password"}, status=403
                )

    if None not in users_db.get_user(new_user_username):
        return web.json_response({"error": "Username already exists"}, status=400)

    users_db.add_user(
        str(uuid.uuid4()),
        new_user_username,
        new_user_password,
        not bool(admin_user_id),
    )

    logger.registration_success(
        ip, new_user_username, username if admin_user_id is not None else None
    )
    timeout.remove_failed_attempts(ip)
    return web.json_response({"message": "User registered successfully"})


@routes.get("/login")
async def get_login(request: web.Request) -> web.Response:
    if not users_db.load_users():
        return web.HTTPFound("/register")

    token = jwt_auth.get_token_from_request(request)
    if token:
        return web.HTTPFound("/logout")
    return web.FileResponse(os.path.join(HTML_DIR, "login.html"))


@routes.get("/generate_token")
async def get_generate_token(request: web.Request) -> web.Response:
    with open(os.path.join(HTML_DIR, "generate_token.html"), "r") as f:
        html_content = f.read()

    if not users_db.load_users():
        html_content = html_content.replace("{{ X-Admin-User }}", "true")
    html_content = html_content.replace("{{ X-Admin-User }}", "false")

    return web.Response(body=html_content, content_type="text/html")

@routes.post("/generate_token")
async def post_generate_token(request: web.Request) -> web.Response:
    sanitized_data = request.get("_sanitized_data", {})
    ip = get_ip(request)
    username = sanitized_data.get("username")
    password = sanitized_data.get("password")
    logger.log_message("DEBUG", str(type(sanitized_data.get("expire_hours"))))
    try:
        expire_hours = int(sanitized_data.get("expire_hours"))
    except ValueError:
        return web.json_response(
            {"error": "Invalid value ({}) for expire_hours".format(sanitized_data.get("expire_hours"))}, status=400
        )
    except TypeError:
        return web.json_response(
            {"error": "Missing expire_hours"}, status=400
        )
    if expire_hours>87600:
       return web.json_response(
            {"error": "expire_hours ({}) over the limit of 87600 (10 years)".format(expire_hours)}, status=400
        )

    if not username or not password:
        return web.json_response(
            {"error": "Missing login credentials (username and password)"}, status=400
        )
    

    if users_db.check_username_password(username, password):
        timeout.remove_failed_attempts(ip)

        user_id, _ = users_db.get_user(username)
        token = jwt_auth.create_access_token({"id": user_id, "username": username},expire_minutes=(expire_hours*60))
        response = web.json_response(
            {
                "message": "Token successfully generated",
                "jwt_token": token,
            }
        )
        secure_flag = request.headers.get("X-Forwarded-Proto", "http") == "https"
        response.set_cookie(
           "jwt_token", token, httponly=True, secure=secure_flag, samesite="Strict"
        )
        logger.log_message("INFO", "Token generated for {}".format(username))
        return response

    logger.log_message("INFO", "Token failed to be generated for {}".format(username))
    timeout.add_failed_attempt(ip)
    return web.json_response({"error": "Invalid username or password"}, status=401)

@routes.post("/login")
async def post_login(request: web.Request) -> web.Response:
    sanitized_data = request.get("_sanitized_data", {})
    ip = get_ip(request)
    username = sanitized_data.get("username")
    password = sanitized_data.get("password")

    if not username or not password:
        return web.json_response(
            {"error": "Missing login credentials (username and password)"}, status=400
        )

    if users_db.check_username_password(username, password):
        timeout.remove_failed_attempts(ip)

        user_id, _ = users_db.get_user(username)
        token = jwt_auth.create_access_token({"id": user_id, "username": username})
        response = web.json_response(
            {
                "message": "Login successful",
                "jwt_token": token,
                # "user_settings_id": next((key for key, value in instance.user_manager.users.items() if value == username), ""),
            }
        )
        secure_flag = request.headers.get("X-Forwarded-Proto", "http") == "https"
        response.set_cookie(
            "jwt_token", token, httponly=True, secure=secure_flag, samesite="Strict"
        )
        logger.login_success(ip, username)
        return response

    logger.login_attempt(ip, username, password)
    timeout.add_failed_attempt(ip)
    return web.json_response({"error": "Invalid username or password"}, status=401)


@routes.get("/logout")
async def get_logout(request: web.Request) -> web.Response:
    ip = get_ip(request)
    free_memory = request.query.get("free_memory", "false").lower() == "true"
    unload_models = request.query.get("unload_models", "false").lower() == "true"

    token = jwt_auth.get_token_from_request(request)
    if token and FREE_MEMORY_ON_LOGOUT:
        try:
            username = jwt_auth.decode_access_token(token).get("username")
            if free_memory or unload_models:
                if hasattr(instance, "post_free"):
                    json_data = {
                        "unload_models": unload_models,
                        "free_memory": free_memory,
                    }
                    mock_request = web.Request(
                        app=app,
                        method="POST",
                        path="/free",
                        headers={},
                        match_info={},
                        payload=None,
                    )
                    mock_request._post = json_data
                    await instance.post_free(mock_request)
                    logger.memory_free(ip, username, free_memory, unload_models)

            logger.logout(ip, username)
        except jwt.ExpiredSignatureError:
            pass
        except jwt.InvalidTokenError:
            pass
        except Exception as e:
            logger.error(f"Unexpected error during logout: {e}")

    response = web.HTTPFound("/login")
    response.del_cookie("jwt_token", path="/")

    return response


app.add_routes(
    [
        web.static("/sentinel/css", CSS_DIR),
        web.static("/sentinel/js", JS_DIR),
        web.static("/sentinel/assets", ASSETS_DIR),
    ]
)

if FORCE_HTTPS:
    app.middlewares.append(create_https_middleware(MATCH_HEADERS))

app.middlewares.append(ip_filter.create_ip_filter_middleware())
app.middlewares.append(sanitizer.create_sanitizer_middleware())
app.middlewares.append(
    timeout.create_time_out_middleware(limited=("/login", "/register", "/generate_token"))
)
app.middlewares.append(
    jwt_auth.create_jwt_middleware(
        public=("/login", "/logout", "/register", "/generate_token"), public_prefixes=("/sentinel")
    )
)

if SEPERATE_USERS:
    app.middlewares.append(access_control.create_folder_access_control_middleware())

    access_control.patch_folder_paths()
    access_control.patch_prompt_queue()

if MANAGER_ADMIN_ONLY:
    app.middlewares.append(access_control.create_manager_access_control_middleware(manager_directory="/extensions/comfyui-manager", manager_routes=("api/customnode",  "api/snapshot", "/api/manager", "api/comfyui_manager", "api/externalmodel")))