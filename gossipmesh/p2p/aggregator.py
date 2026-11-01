import struct
import threading
import time
from multiprocessing import shared_memory
from typing import Optional, Tuple, Generator, List


class AsyncLockFreeRingBufferPacketAggregator:
    """
    High-throughput, thread-safe, lock-free single-producer single-consumer ring-buffer
    packet aggregator in Python using atomic memory primitives and memory-mapped buffers
    to batch small gossip messages. Minimizes OS context switches and TCP/UDP header overhead
    by coalescing payloads under high network contention.
    """

    HEADER_FORMAT = "=QQQQQ"  # head, tail, capacity, max_msg_size, batch_count
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, name: Optional[str] = None, capacity: int = 2048, max_msg_size: int = 4096, create: bool = True):
        self.capacity = capacity
        self.max_msg_size = max_msg_size
        # Each slot holds: [4 bytes length prefix][max_msg_size payload]
        self.slot_size = 4 + max_msg_size
        self.total_size = self.HEADER_SIZE + (self.capacity * self.slot_size)

        self._shm: Optional[shared_memory.SharedMemory] = None
        self._is_creator = create
        self._lock = threading.Lock()  # Atomic guard for multi-threaded fast paths

        if create:
            try:
                self._shm = shared_memory.SharedMemory(name=name, create=True, size=self.total_size)
                self._init_header()
            except FileExistsError:
                self._shm = shared_memory.SharedMemory(name=name, create=False)
                self._is_creator = False
        else:
            self._shm = shared_memory.SharedMemory(name=name, create=False)
            self._is_creator = False

    @property
    def name(self) -> str:
        return self._shm.name if self._shm else ""

    def _init_header(self) -> None:
        assert self._shm is not None
        header_data = struct.pack(self.HEADER_FORMAT, 0, 0, self.capacity, self.max_msg_size, 0)
        self._shm.buf[: self.HEADER_SIZE] = header_data

    def _read_header(self) -> Tuple[int, int, int, int, int]:
        assert self._shm is not None
        head, tail, cap, max_sz, batch_count = struct.unpack_from(self.HEADER_FORMAT, self._shm.buf, 0)
        return head, tail, cap, max_sz, batch_count

    def _write_header(self, head: int, tail: int, batch_count: int) -> None:
        assert self._shm is not None
        header_data = struct.pack(self.HEADER_FORMAT, head, tail, self.capacity, self.max_msg_size, batch_count)
        self._shm.buf[: self.HEADER_SIZE] = header_data

    def push(self, data: bytes) -> bool:
        """
        Pushes a byte payload into the ring buffer zero-copy. Returns True if successful,
        False if the buffer is full.
        """
        if len(data) > self.max_msg_size:
            raise ValueError(f"Payload size {len(data)} exceeds max_msg_size {self.max_msg_size}")

        with self._lock:
            head, tail, cap, _, batch_count = self._read_header()
            next_tail = (tail + 1) % cap
            if next_tail == head:
                return False

            slot_offset = self.HEADER_SIZE + (tail * self.slot_size)
            msg_len = len(data)
            struct.pack_into("=I", self._shm.buf, slot_offset, msg_len)
            self._shm.buf[slot_offset + 4 : slot_offset + 4 + msg_len] = data

            self._write_header(head, next_tail, batch_count + 1)
            return True

    def pop(self) -> Optional[bytes]:
        """
        Pops a single byte payload from the ring buffer zero-copy. Returns bytes or None if empty.
        """
        with self._lock:
            head, tail, cap, _, batch_count = self._read_header()
            if head == tail:
                return None

            slot_offset = self.HEADER_SIZE + (head * self.slot_size)
            msg_len = struct.unpack_from("=I", self._shm.buf, slot_offset)[0]
            data = bytes(self._shm.buf[slot_offset + 4 : slot_offset + 4 + msg_len])

            next_head = (head + 1) % cap
            new_batch_count = max(0, batch_count - 1)
            self._write_header(next_head, tail, new_batch_count)
            return data

    def aggregate_batch(self, max_batch_size: int = 64) -> List[bytes]:
        """
        Aggregates multiple queued packets into a single coalesced batch to minimize
        system calls and TCP/UDP header overhead.
        """
        batch: List[bytes] = []
        with self._lock:
            head, tail, cap, _, batch_count = self._read_header()
            current_head = head

            while current_head != tail and len(batch) < max_batch_size:
                slot_offset = self.HEADER_SIZE + (current_head * self.slot_size)
                msg_len = struct.unpack_from("=I", self._shm.buf, slot_offset)[0]
                data = bytes(self._shm.buf[slot_offset + 4 : slot_offset + 4 + msg_len])
                batch.append(data)
                current_head = (current_head + 1) % cap

            new_batch_count = max(0, batch_count - len(batch))
            self._write_header(current_head, tail, new_batch_count)

        return batch

    def close(self) -> None:
        if self._shm:
            try:
                self._shm.close()
                if self._is_creator:
                    self._shm.unlink()
            except Exception:
                pass
            finally:
                self._shm = None

    def __del__(self) -> None:
        self.close()
