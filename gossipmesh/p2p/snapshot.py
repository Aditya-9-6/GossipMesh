import json
import zlib
import hashlib
from typing import Dict, Any, List


class SnapshotTransferProtocol:
    """Handles compressed chunk-based snapshot transfer with cryptographic integrity checks."""

    def __init__(self, chunk_size: int = 1024):
        self.chunk_size = chunk_size

    def serialize_and_chunk(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_data = json.dumps(snapshot, sort_keys=True).encode("utf-8")
        compressed = zlib.compress(raw_data)
        checksum = hashlib.sha256(compressed).hexdigest()

        chunks = []
        total_size = len(compressed)
        for i in range(0, total_size, self.chunk_size):
            chunk_bytes = compressed[i : i + self.chunk_size]
            chunks.append({"offset": i, "total_size": total_size, "data": chunk_bytes.hex(), "checksum": checksum})
        return chunks

    def reassemble_and_verify(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not chunks:
            raise ValueError("No chunks provided for reassembly")

        sorted_chunks = sorted(chunks, key=lambda c: c["offset"])
        expected_checksum = sorted_chunks[0]["checksum"]
        total_size = sorted_chunks[0]["total_size"]

        reassembled = bytearray()
        for chunk in sorted_chunks:
            reassembled.extend(bytes.fromhex(chunk["data"]))

        if len(reassembled) != total_size:
            raise ValueError("Reassembled snapshot size mismatch")

        actual_checksum = hashlib.sha256(bytes(reassembled)).hexdigest()
        if actual_checksum != expected_checksum:
            raise ValueError("Snapshot checksum verification failed")

        decompressed = zlib.decompress(bytes(reassembled))
        return json.loads(decompressed.decode("utf-8"))
