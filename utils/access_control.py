import os
import heapq
import copy
import contextvars
from aiohttp import web
from typing import Optional

import folder_paths
from server import PromptServer
from execution import PromptQueue, MAXIMUM_HISTORY_SIZE

from .users_db import UsersDB


class AccessControl:
    def __init__(self, users_db: UsersDB, server: PromptServer):
        self.users_db = users_db
        self.server = server

        self._current_user = contextvars.ContextVar("user_id", default=None)
        self.__current_user_id = None

        self.__get_output_directory = folder_paths.get_output_directory
        self.__get_temp_directory = folder_paths.get_temp_directory
        self.__get_input_directory = folder_paths.get_input_directory

        self.__prompt_queue = self.server.prompt_queue
        self.__prompt_queue_put = self.__prompt_queue.put

    @property
    def folder_paths(self) -> tuple:
        return (
            self.__get_output_directory(),
            self.__get_temp_directory(),
            self.__get_input_directory(),
        )

    def set_current_user_id(self, user_id: str, set_fallback: bool = False) -> None:
        """Set the current user directory from ID."""
        self._current_user.set(user_id)

        if set_fallback:
            self.__current_user_id = user_id

    def get_current_user_id(self) -> str:
        """Retrieve the current user directory from ID."""
        if self._current_user.get():
            return self._current_user.get()

        return self.__current_user_id

    def get_user_output_directory(self) -> str:
        """Get the user-specific output directory."""
        return os.path.join(
            self.__get_output_directory(),
            self.get_current_user_id() or "public",
        )

    def get_user_temp_directory(self) -> str:
        """Get the user-specific temp directory."""
        return os.path.join(
            self.__get_temp_directory(),
            self.get_current_user_id() or "public",
        )

    def get_user_input_directory(self) -> str:
        """Get the user-specific input directory."""
        input_directory = os.path.join(
            self.__get_input_directory(),
            self.get_current_user_id() or "public",
        )

        os.makedirs(input_directory, exist_ok=True)

        return input_directory

    def add_user_specific_folder_paths(self, json_data) -> None:
        """Add user-specific folder paths to the prompt JSON data."""
        user_id = self.get_current_user_id() or "public"

        if isinstance(json_data, dict):
            for key, value in json_data.items():
                if key == "filename_prefix":
                    json_data[key] = f"{user_id}/{value}"
                else:
                    self.add_user_specific_folder_paths(value)
        elif isinstance(json_data, list):
            for item in json_data:
                self.add_user_specific_folder_paths(item)

        return json_data

    def patch_folder_paths(self) -> None:
        """Patch the folder_paths with user-specific methods."""
        # folder_paths.get_output_directory = self.get_user_output_directory
        folder_paths.get_temp_directory = self.get_user_temp_directory
        folder_paths.get_input_directory = self.get_user_input_directory

        self.server.add_on_prompt_handler(self.add_user_specific_folder_paths)

    def create_folder_access_control_middleware(
        self, folder_paths: tuple = ()
    ) -> web.middleware:
        """Create middleware for folder access control."""

        folder_paths = folder_paths or self.folder_paths

        @web.middleware
        async def folder_access_control_middleware(
            request: web.Request, handler
        ) -> web.Response:
            """Middleware to handle folder access control."""
            if not request.path.startswith(folder_paths):
                return await handler(request)

            user_id = request.get("user_id")

            user_id, user = self.users_db.get_user(user_id)

            try:
                path_parts = request.path.strip("/").split("/")
                folder_user_id = path_parts[1]
            except:
                return web.HTTPNotFound(reason="Folder not found.")

            if folder_user_id == "public":
                return await handler(request)

            if (
                not user_id
                or not user
                or len(path_parts) < 2
                or (user_id != folder_user_id and not user.get("admin"))
            ):
                return web.HTTPForbidden(
                    reason="You do not have access to this folder."
                )

            return await handler(request)

        return folder_access_control_middleware

    def user_queue_put(self, item):
        """Put an item in the user-specific queue."""
        item = {"prompt": item, "user_id": self.get_current_user_id()}
        self.__prompt_queue_put(item)

    def user_queue_get(self, timeout=None):
        """Get an item from the user-specific queue."""
        user_queue = self.__prompt_queue.queue
        with self.__prompt_queue.not_empty:
            while len(user_queue) == 0:
                self.__prompt_queue.not_empty.wait(timeout=timeout)
                if timeout is not None and len(user_queue) == 0:
                    return None
            item = heapq.heappop(user_queue)
            i = self.__prompt_queue.task_counter
            self.__prompt_queue.currently_running[i] = copy.deepcopy(item)
            self.__prompt_queue.task_counter += 1
            self.server.queue_updated()
            return (item["prompt"], i)

    def user_queue_task_done(
        self, item_id, history_result, status: Optional["PromptQueue.ExecutionStatus"]
    ):
        """Mark a user-specific queue task as done."""
        with self.__prompt_queue.mutex:
            prompt = self.__prompt_queue.currently_running.pop(item_id)
            if len(self.__prompt_queue.history) > MAXIMUM_HISTORY_SIZE:
                self.__prompt_queue.history.pop(next(iter(self.__prompt_queue.history)))

            status_dict: Optional[dict] = None
            if status is not None:
                status_dict = copy.deepcopy(status._asdict())

            self.__prompt_queue.history[prompt["prompt"][1]] = {
                "prompt": prompt["prompt"],
                "outputs": {},
                "status": status_dict,
                "user_id": prompt["user_id"],
            }
            self.__prompt_queue.history[prompt["prompt"][1]].update(history_result)
            self.server.queue_updated()

    def user_queue_get_current_queue(self):
        """Get the current user-specific queue."""
        with self.__prompt_queue.mutex:
            out = []
            for x in self.__prompt_queue.currently_running.values():
                out += [x]
            return (out, copy.deepcopy(self.__prompt_queue.queue))

    def user_queue_wipe_queue(self):
        """Wipe the user-specific queue."""
        with self.__prompt_queue.mutex:
            self.__prompt_queue.queue = [
                item
                for item in self.__prompt_queue.queue
                if item["user_id"] != self.get_current_user_id()
            ]
            self.server.queue_updated()

    def user_queue_delete_queue_item(self, function):
        """Delete an item from the user-specific queue."""
        with self.__prompt_queue.mutex:
            for x in range(len(self.__prompt_queue.queue)):
                if (
                    function(self.__prompt_queue.queue[x])
                    and self.__prompt_queue.queue[x]["user_id"]
                    == self.get_current_user_id()
                ):
                    if len(self.__prompt_queue.queue) == 1:
                        self.__prompt_queue.wipe_queue()
                    else:
                        self.__prompt_queue.pop(x)
                        heapq.heapify(self.__prompt_queue.queue)
                    self.server.queue_updated()
                    return True
        return False

    def user_queue_get_history(self, prompt_id=None, max_items=None, offset=-1):
        """Get the user-specific queue history."""
        with self.__prompt_queue.mutex:
            user_history = {
                k: v
                for k, v in self.__prompt_queue.history.items()
                if v["user_id"] == self.get_current_user_id()
            }
            if prompt_id is None:
                out = {}
                i = 0
                if offset < 0 and max_items is not None:
                    offset = len(self.__prompt_queue.history) - max_items
                for k in user_history:
                    if i >= offset:
                        out[k] = user_history[k]
                        if max_items is not None and len(out) >= max_items:
                            break
                    i += 1
                return out
            elif prompt_id in user_history:
                return {prompt_id: copy.deepcopy(user_history[prompt_id])}
            else:
                return {}

    def user_queue_wipe_history(self):
        """Wipe the user-specific queue history."""
        with self.__prompt_queue.mutex:
            self.__prompt_queue.history = {
                k: v
                for k, v in self.__prompt_queue.history.items()
                if v["user_id"] != self.get_current_user_id()
            }

    def patch_prompt_queue(self):
        """Patch the prompt queue with user-specific methods."""
        self.__prompt_queue.put = self.user_queue_put
        self.__prompt_queue.get = self.user_queue_get
        self.__prompt_queue.task_done = self.user_queue_task_done
        self.__prompt_queue.get_current_queue = self.user_queue_get_current_queue
        self.__prompt_queue.wipe_queue = self.user_queue_wipe_queue
        self.__prompt_queue.delete_queue_item = self.user_queue_delete_queue_item
        self.__prompt_queue.get_history = self.user_queue_get_history
        self.__prompt_queue.wipe_history = self.user_queue_wipe_history

    def create_manager_access_control_middleware(
        self, manager_directory: str = "/extensions/comfyui-manager", manager_routes: tuple = ()
    ) -> web.middleware:
        """Create middleware for manager access control."""

        @web.middleware
        async def manager_access_control_middleware(
            request: web.Request, handler
        ) -> web.Response:
            """Middleware to handle manager access control."""
            user_id = request.get("user_id")
            
            if self.users_db.get_admin_user()[0] == user_id or (not request.path.startswith(manager_routes) and not request.path.lower().startswith(manager_directory)):
                return await handler(request)

            return web.HTTPForbidden(
                reason="You do not have access to comfyui manager."
            )

        return manager_access_control_middleware
