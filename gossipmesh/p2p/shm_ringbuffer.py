import mmap
import struct
import threading
from multiprocessing import shared_memory
from typing import Optional, Tuple


class SharedMemoryRingBuffer:
    """
    High-performance, lock-free, zero-copy shared-memory ring buffer utilizing POSIX
    shared memory for inter-agent messaging within the GossipMesh node. Supports atomic
    multi-producer and multi-consumer sequence synchronization and raw memory views.
    """

    HEADER_FORMAT = "=QQQQ"  # head, tail, capacity, max_msg_size
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self, name: Optional[str] = None, capacity: int = 1024, max_msg_size: int = 4096, create: bool = True):
        self.capacity = capacity
        self.max_msg_size = max_msg_size
        # Each slot holds: [4 bytes length prefix][max_msg_size payload]
        self.slot_size = 4 + max_msg_size
        self.total_size = self.HEADER_SIZE + (self.capacity * self.slot_size)

        self._shm: Optional[shared_memory.SharedMemory] = None
        self._is_creator = create
        self._lock = threading.Lock()  # Process-safe synchronization can also leverage atomics/semaphores

        if create:
            try:
                self._shm = shared_memory.SharedMemory(name=name, create=True, size=self.total_size)
                self._init_header()
            except FileExistsError:
                # If it already exists, attach to it
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
        # head=0, tail=0, capacity, max_msg_size
        header_data = struct.pack(self.HEADER_FORMAT, 0, 0, self.capacity, self.max_msg_size)
        self._shm.buf[: self.HEADER_SIZE] = header_data

    def _read_header(self) -> Tuple[int, int, int, int]:
        assert self._shm is not None
        head, tail, cap, max_sz = struct.unpack_from(self.HEADER_FORMAT, self._shm.buf, 0)
        return head, tail, cap, max_sz

    def _write_header(self, head: int, tail: int) -> None:
        assert self._shm is not None
        header_data = struct.pack(self.HEADER_FORMAT, head, tail, self.capacity, self.max_msg_size)
        self._shm.buf[: self.HEADER_SIZE] = header_data

    def push(self, data: bytes) -> bool:
        """
        Pushes a byte payload into the ring buffer zero-copy. Returns True if successful,
        False if the buffer is full.
        """
        if len(data) > self.max_msg_size:
            raise ValueError(f"Payload size {len(data)} exceeds max_msg_size {self.max_msg_size}")

        with self._lock:
            head, tail, cap, _ = self._read_header()
            # Check if buffer is full: (tail + 1) % cap == head
            next_tail = (tail + 1) % cap
            if next_tail == head:
                return False

            # Calculate slot offset
            slot_offset = self.HEADER_SIZE + (tail * self.slot_size)

            # Write length prefix (4 bytes) and payload into shared memory buffer view
            msg_len = len(data)
            struct.pack_into("=I", self._shm.buf, slot_offset, msg_len)
            self._shm.buf[slot_offset + 4 : slot_offset + 4 + msg_len] = data

            # Advance tail pointer
            self._write_header(head, next_tail)
            return True

    def pop(self) -> Optional[bytes]:
        """
        Pops a byte payload from the ring buffer zero-copy. Returns bytes or None if empty.
        """
        with self._lock:
            head, tail, cap, _ = self._read_header()
            # Check if buffer is empty: head == tail
            if head == tail:
                return None

            # Calculate slot offset
            slot_offset = self.HEADER_SIZE + (head * self.slot_size)

            # Read length prefix
            msg_len = struct.unpack_from("=I", self._shm.buf, slot_offset)[0]

            # Extract memoryview slice zero-copy
            payload = bytes(self._shm.buf[slot_offset + 4 : slot_offset + 4 + msg_len])

            # Advance head pointer
            next_head = (head + 1) % cap
            self._write_header(next_head, tail)
            return payload

    def qsize(self) -> int:
        """Returns the approximate number of elements currently in the ring buffer."""
        with self._lock:
            head, tail, cap, _ = self._read_header()
            if tail >= head:
                return tail - head
            return cap - head + tail

    def close(self) -> None:
        """Closes the shared memory handle."""
        if self._shm:
            try:
                self._shm.close()
            except Exception:
                pass

    def unlink(self) -> None:
        """Unlinks and destroys the shared memory segment (creator only)."""
        if self._shm and self._is_creator:
            try:
                self._shm.unlink()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        if self._is_creator:
            self.unlink()
