import asyncio
import threading
import socket
import contextlib
import websockets
from typing import Optional  # 3.9 호환

def _get_lan_ip() -> str:
    """현재 PC의 LAN IP (예: 192.168.x.x). 실패 시 127.0.0.1."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class WebSocketServer:
    """
    - 별도 스레드에서 asyncio.run(...)으로 서버 실행
    - 0.0.0.0 바인딩 → 같은 Wi-Fi 실기기 접근 가능
    - set_direction("UP"/"DOWN"/"LEFT"/"RIGHT"/"NONE") 값 주기적 브로드캐스트
    """
    def __init__(self, host: str = "0.0.0.0", port: int = 8765, interval: float = 0.2):
        self.host = host
        self.port = port
        self.interval = interval

        self._direction = "NONE"
        self._clients = set()

        self._stop_flag = threading.Event()
        self._thread: Optional[threading.Thread] = None  # 3.9 호환 표기

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_flag.set()
        if self._thread:
            self._thread.join(timeout=2)

    def set_direction(self, direction: str):
        self._direction = direction

    async def _handler(self, websocket):
        self._clients.add(websocket)
        try:
            async for _ in websocket:  # 클라이언트 메시지는 무시
                pass
        except Exception:
            pass
        finally:
            self._clients.discard(websocket)

    async def _broadcast_task(self):
        while not self._stop_flag.is_set():
            if self._clients:
                msg = self._direction
                dead = []
                for ws in list(self._clients):
                    try:
                        await ws.send(msg)
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    self._clients.discard(ws)
            await asyncio.sleep(self.interval)

    async def _amain(self):
        async with websockets.serve(self._handler, self.host, self.port):
            print(
                f"WebSocket server started. Connect from your app using: "
                f"ws://{_get_lan_ip()}:{self.port}"
            )
            broadcaster = asyncio.create_task(self._broadcast_task())
            try:
                while not self._stop_flag.is_set():
                    await asyncio.sleep(0.2)
            finally:
                broadcaster.cancel()
                with contextlib.suppress(Exception):
                    await broadcaster

    def _run(self):
        try:
            asyncio.run(self._amain())
        except Exception as e:
            import traceback
            print("WS loop crashed:", e)
            traceback.print_exc()
