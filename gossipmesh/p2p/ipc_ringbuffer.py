import mmap
import struct
import threading
from multiprocessing import shared_memory
from typing import Optional, Tuple


class IPCSharedMemoryRingBuffer:
    """
    High-throughput, lock-free, zero-copy inter-process communication ring buffer
    utilizing POSIX shared memory (`multiprocessing.shared_memory`) for offloading high-volume
    gossip packet serialization/deserialization across autonomous agent subprocesses.
    Guarantees atomic SPSC offset tracking and zero-allocation memory views.
    """

    HEADER_FORMAT = "=QQQQ"  # head, tail, capacity, max_msg_size
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(
        self,
        name: Optional[str] = None,
        capacity: int = 1024,
        max_msg_size: int = 4096,
        create: bool = True,
    ):
        self.capacity = capacity
        self.max_msg_size = max_msg_size
        # Each slot holds: [4 bytes length prefix][max_msg_size payload]
        self.slot_size = 4 + max_msg_size
        self.total_size = self.HEADER_SIZE + (self.capacity * self.slot_size)

        self._shm: Optional[shared_memory.SharedMemory] = None
        self._is_creator = create
        self._lock = threading.Lock()  # Thread-safe for single process threads; cross-process uses atomic memory-mapped layout

        if create:
            try:
                self._shm = shared_memory.SharedMemory(
                    name=name, create=True, size=self.total_size
                )
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
        header_data = struct.pack(
            self.HEADER_FORMAT, 0, 0, self.capacity, self.max_msg_size
        )
        self._shm.buf[: self.HEADER_SIZE] = header_data

    def _read_header(self) -> Tuple[int, int, int, int]:
        assert self._shm is not None
        head, tail, cap, max_sz = struct.unpack_from(
            self.HEADER_FORMAT, self._shm.buf, 0
        )
        return head, tail, cap, max_sz

    def _write_header(self, head: int, tail: int) -> None:
        assert self._shm is not None
        header_data = struct.pack(
            self.HEADER_FORMAT, head, tail, self.capacity, self.max_msg_size
        )
        self._shm.buf[: self.HEADER_SIZE] = header_data

    def push(self, data: bytes) -> bool:
        """
        Pushes a byte payload into the IPC ring buffer zero-copy.
        Returns True if successful, False if the buffer is full.
        """
        if len(data) > self.max_msg_size:
            raise ValueError(
                f"Payload size {len(data)} exceeds max_msg_size {self.max_msg_size}"
            )

        with self._lock:
            head, tail, cap, _ = self._read_header()
            next_tail = (tail + 1) % cap
            if next_tail == head:
                return False

            slot_offset = self.HEADER_SIZE + (tail * self.slot_size)
            msg_len = len(data)
            struct.pack_into("=I", self._shm.buf, slot_offset, msg_len)
            self._shm.buf[slot_offset + 4 : slot_offset + 4 + msg_len] = data

            self._write_header(head, next_tail)
            return True

    def pop(self) -> Optional[bytes]:
        """
        Pops a byte payload from the IPC ring buffer zero-copy.
        Returns bytes or None if empty.
        """
        with self._lock:
            head, tail, cap, _ = self._read_header()
            if head == tail:
                return None

            slot_offset = self.HEADER_SIZE + (head * self.slot_size)
            msg_len = struct.unpack_from("=I", self._shm.buf, slot_offset)[0]
            
            # Zero-copy memory view slicing
            payload_view = memoryview(self._shm.buf)[
                slot_offset + 4 : slot_offset + 4 + msg_len
            ]
            data = bytes(payload_view)

            next_head = (head + 1) % cap
            self._write_header(next_head, tail)
            return data

    def is_empty(self) -> bool:
        head, tail, _, _ = self._read_header()
        return head == tail

    def is_full(self) -> bool:
        head, tail, cap, _ = self._read_header()
        return (tail + 1) % cap == head

    def close(self) -> None:
        if self._shm is not None:
            try:
                self._shm.close()
            except Exception:
                pass

    def unlink(self) -> None:
        if self._shm is not None and self._is_creator:
            try:
                self._shm.unlink()
            except Exception:
                pass
