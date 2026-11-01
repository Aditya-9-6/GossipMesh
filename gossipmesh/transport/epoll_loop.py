import select
import socket
import logging
from typing import Callable, Dict, Optional
from gossipmesh.transport.mmap_ring import MMapCircularRingBuffer

logger = logging.getLogger(__name__)


class EpollEventLoop:
    """
    High-performance epoll-driven non-blocking event loop integrated with
    memory-mapped circular ring buffers for lightning-fast packet ingestion.
    """

    def __init__(self, ring_buffer: MMapCircularRingBuffer) -> None:
        self.ring_buffer = ring_buffer
        self._epoll = select.epoll()
        self._sockets: Dict[int, socket.socket] = {}
        self._callbacks: Dict[int, Callable[[socket.socket], None]] = {}
        self._running = False

    def register_socket(
        self,
        sock: socket.socket,
        events: int = select.EPOLLIN,
        callback: Optional[Callable[[socket.socket], None]] = None,
    ) -> None:
        sock.setblocking(False)
        fd = sock.fileno()
        self._sockets[fd] = sock
        self._epoll.register(fd, events)
        if callback:
            self._callbacks[fd] = callback

    def unregister_socket(self, sock: socket.socket) -> None:
        fd = sock.fileno()
        if fd in self._sockets:
            try:
                self._epoll.unregister(fd)
            except Exception:
                pass
            del self._sockets[fd]
            self._callbacks.pop(fd, None)

    def handle_packet_data(self, sock: socket.socket) -> None:
        try:
            data, addr = sock.recvfrom(65535)
            if data:
                success = self.ring_buffer.write(data)
                if not success:
                    logger.warning("Ring buffer full during epoll packet ingestion; packet dropped.")
        except BlockingIOError:
            pass
        except Exception as e:
            logger.error(f"Error reading from socket in epoll loop: {e}")

    def run_once(self, timeout: float = 0.1) -> int:
        events = self._epoll.poll(timeout)
        for fd, event in events:
            sock = self._sockets.get(fd)
            if not sock:
                continue
            if event & select.EPOLLIN:
                if fd in self._callbacks:
                    self._callbacks[fd](sock)
                else:
                    self.handle_packet_data(sock)
            elif event & (select.EPOLLERR | select.EPOLLHUP):
                self.unregister_socket(sock)
        return len(events)

    def stop(self) -> None:
        self._running = False
        try:
            self._epoll.close()
        except Exception:
            pass
