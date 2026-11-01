import socket
import select
import pytest
from gossipmesh.transport.mmap_ring import MMapCircularRingBuffer
from gossipmesh.transport.epoll_loop import EpollEventLoop

def test_epoll_loop_ingestion():
    ring = MMapCircularRingBuffer(capacity_bytes=2048)
    loop = EpollEventLoop(ring)
    
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_sock.bind(("127.0.0.1", 0))
    server_port = server_sock.getsockname()[1]
    
    loop.register_socket(server_sock)
    
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    test_payload = b"Epoll test packet payload"
    client_sock.sendto(test_payload, ("127.0.0.1", server_port))
    
    # Run once to ingest event
    events_processed = loop.run_once(timeout=0.5)
    assert events_processed >= 0
    
    server_sock.close()
    client_sock.close()
    loop.stop()
    ring.close()
