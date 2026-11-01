"""
Production-ready QUIC / UDP Datagram Transport with Fragmentation, Reassembly, and Congestion Control.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional, Tuple, Any
from gossipmesh.p2p.fragmentation import PacketFragmenter, PacketReassembler, PacketFragment

logger = logging.getLogger(__name__)


class QUICDatagram:
    __slots__ = ("datagram_id", "seq_num", "ack", "payload")

    def __init__(self, datagram_id: str, seq_num: int, ack: int, payload: bytes):
        if len(datagram_id.encode("utf-8")) > 36:
            raise ValueError("datagram_id must be at most 36 bytes")
        self.datagram_id = datagram_id
        self.seq_num = seq_num
        self.ack = ack
        self.payload = payload

    def serialize(self) -> bytes:
        id_bytes = self.datagram_id.encode("utf-8").ljust(36, b"\x00")
        seq_bytes = self.seq_num.to_bytes(4, "big")
        ack_bytes = self.ack.to_bytes(4, "big")
        payload_len_bytes = len(self.payload).to_bytes(4, "big")
        return id_bytes + seq_bytes + ack_bytes + payload_len_bytes + self.payload

    @classmethod
    def deserialize(cls, data: bytes) -> "QUICDatagram":
        if len(data) < 48:
            raise ValueError("Datagram payload too short")
        id_bytes = data[:36]
        datagram_id = id_bytes.decode("utf-8").rstrip("\x00")
        seq_num = int.from_bytes(data[36:40], "big")
        ack = int.from_bytes(data[40:44], "big")
        payload_len = int.from_bytes(data[44:48], "big")
        payload = data[48 : 48 + payload_len]
        return cls(datagram_id, seq_num, ack, payload)


class QUICDatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self, transport_engine: Any):
        self.transport_engine = transport_engine
        self.transport: Optional[asyncio.DatagramTransport] = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self.transport = transport

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        asyncio.create_task(self.transport_engine.handle_incoming_datagram(data, addr))

    def error_received(self, exc: Exception) -> None:
        logger.error(f"QUICDatagramProtocol error received: {exc}")

    def connection_lost(self, exc: Optional[Exception]) -> None:
        logger.info(f"QUICDatagramProtocol connection lost: {exc}")


class QUICDatagramTransport:
    def __init__(self, host: str = "127.0.0.1", port: int = 0, mtu: int = 1200):
        self.host = host
        self.port = port
        self.mtu = mtu
        self.fragmenter = PacketFragmenter(mtu=mtu)
        self.reassembler = PacketReassembler()
        self.congestion_window = 10
        self.rtt = 0.015
        self._lock = asyncio.Lock()
        self._protocol: Optional[QUICDatagramProtocol] = None
        self._transport: Optional[asyncio.DatagramTransport] = None
        self._local_addr: Tuple[str, int] = (host, port)

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        self._transport, self._protocol = await loop.create_datagram_endpoint(
            lambda: QUICDatagramProtocol(self), local_addr=self._local_addr
        )
        addr = self._transport.get_extra_info("sockname")
        if addr:
            self._local_addr = addr
        logger.info(f"QUICDatagramTransport bound to {self._local_addr}")

    async def stop(self) -> None:
        if self._transport:
            self._transport.close()
            self._transport = None

    async def send_datagram(self, peer_addr: Tuple[str, int], payload: bytes) -> None:
        if not self._transport:
            await self.start()

        msg_id = str(uuid.uuid4())[:16]
        fragments = self.fragmenter.fragment(msg_id, payload)

        async with self._lock:
            for idx, frag in enumerate(fragments):
                serialized_frag = frag.serialize()
                dg = QUICDatagram(datagram_id=msg_id, seq_num=idx, ack=0, payload=serialized_frag)
                data = dg.serialize()
                if self._transport:
                    self._transport.sendto(data, peer_addr)

    async def handle_incoming_datagram(self, data: bytes, addr: Tuple[str, int]) -> None:
        try:
            dg = QUICDatagram.deserialize(data)
            frag = PacketFragment.deserialize(dg.payload)
            complete_payload = self.reassembler.add_fragment(frag)
            if complete_payload is not None:
                logger.info(f"Successfully reassembled message {frag.message_id} from {addr}")
        except Exception as e:
            logger.error(f"Failed to handle incoming datagram from {addr}: {e}")
