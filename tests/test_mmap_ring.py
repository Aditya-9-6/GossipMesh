import concurrent.futures
from gossipmesh.transport.mmap_ring import MMapCircularRingBuffer


class TestMMapRing:
    def test_basic_write_read(self):
        buf = MMapCircularRingBuffer(size=4096)
        msg = b"hello gossipmesh"
        assert buf.write(msg) is True
        assert buf.read() == msg
        assert buf.read() is None
        buf.close()

    def test_concurrent_stress(self):
        buf = MMapCircularRingBuffer(size=1024 * 64)
        iterations = 200

        def producer():
            for i in range(iterations):
                buf.write(f"msg-{i}".encode())

        def consumer():
            read_count = 0
            while read_count < iterations:
                res = buf.read()
                if res:
                    read_count += 1

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            f1 = executor.submit(producer)
            f2 = executor.submit(consumer)
            concurrent.futures.wait([f1, f2])

        buf.close()
