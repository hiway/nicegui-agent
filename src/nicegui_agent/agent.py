import asyncio
from typing import Any, Optional, Union

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from socketio import AsyncClient, AsyncServer
from socketio.exceptions import BadNamespaceError



class Agent:
    def __init__(
        self,
        name: str,
        sio: Union[AsyncServer, AsyncClient, None] = None,
        namespace: str = "/agent",
    ):
        self.name = name
        self.namespace = namespace
        self.sio = sio or AsyncClient()
        self._ng_socket_path = "/_nicegui_ws/socket.io"
        self._event_handlers = {}
        self._scheduler = None
        self._scheduled_coros = {}
        self.sio.on("connect", self._on_connect, namespace=namespace)
        self.sio.on("disconnect", self._on_disconnect, namespace=namespace)
        self.sio.on("frame", self._on_frame, namespace=namespace)

    async def _on_connect(self, *args, **kwargs):
        if self._scheduler:
            self._scheduler.resume()

    async def _on_disconnect(self, *args, **kwargs):
        if self._scheduler:
            self._scheduler.pause()

    async def _on_frame(self, *args):
        if len(args) != 1:
            frame = args[1]
        else:
            frame = args[0]
        if frame["kind"] == "event" and frame["name"] in self._event_handlers:
            for handler in self._event_handlers[frame["name"]]:
                await handler(frame["data"])

    def on(self, name: str):
        def wrapper(coro):
            if name in self._event_handlers:
                self._event_handlers[name].append(coro)
            else:
                self._event_handlers[name] = [coro]
            return coro

        return wrapper

    async def emit(self, name: str, data: Any):
        try:
            await self.sio.emit(
                "frame",
                {
                    "kind": "event",
                    "name": name,
                    "data": data,
                    "agent": self.name,
                },
                namespace=self.namespace,
            )
        except BadNamespaceError as error:
            raise ConnectionError("Server Agent is not connected.") from error


    def on_interval(
        self,
        seconds: Optional[float] = None,
        minutes: Optional[float] = None,
        hours: Optional[float] = None,
    ):
        kwargs = {}
        if seconds is not None:
            kwargs["seconds"] = seconds
        if minutes is not None:
            kwargs["minutes"] = minutes
        if hours is not None:
            kwargs["hours"] = hours

        def wrapper(coro):
            self._scheduled_coros[coro] = kwargs
            return coro

        return wrapper

    async def start(self):
        self._scheduler = AsyncIOScheduler()
        for coro, kwargs in self._scheduled_coros.items():
            self._scheduler.add_job(coro, "interval", **kwargs)
        self._scheduler.start()

    async def stop(self):
        if self._scheduler:
            self._scheduler.shutdown()

    async def connect(self, url: str):
        if isinstance(self.sio, AsyncClient):
            await self.sio.connect(
                url, namespaces=[self.namespace], socketio_path=self._ng_socket_path
            )
        else:
            raise RuntimeError("Server Agent cannot connect.")

    async def disconnect(self):
        if isinstance(self.sio, AsyncClient):
            await self.sio.disconnect()
        else:
            raise RuntimeError("Server Agent cannot disconnect.")

    async def run(self, url: str):
        try:
            await self.connect(url=url)
            await self.start()
            while True:
                await asyncio.sleep(1)
        except asyncio.exceptions.CancelledError:
            print("\nStopping...")
        finally:
            await self.stop()
            await self.disconnect()
