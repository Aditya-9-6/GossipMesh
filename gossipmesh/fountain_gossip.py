"""
Hierarchical Two-Phase Gossip Aggregation Tree with Fountain-Code Packet Encapsulation.

Disseminates and aggregates large state snapshots across large-scale clusters without flooding
using Luby Transform (LT) rateless fountain codes, dynamic routing trees, and resilient packet droplets.
"""

from __future__ import annotations

import math
import os
import random
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class FountainConfig:
    chunk_size: int = 1024  # Bytes per source chunk
    max_degree: int = 10
    overhead_factor: float = 1.15
    tree_fanout: int = 4
    aggregation_timeout_sec: float = 5.0


@dataclass
class Droplet:
    session_id: str
    droplet_id: int
    degree: int
    indices: List[int]
    data: bytes
    total_chunks: int

    def serialize(self) -> bytes:
        """Packs droplet metadata and payload into a compact binary byte string."""
        sid_bytes = self.session_id.encode("utf-8")
        sid_len = len(sid_bytes)
        idx_count = len(self.indices)
        # Header format: sid_len(H), droplet_id(Q), degree(H), total_chunks(H), idx_count(H), indices(...), data_len(I), data(...)
        indices_format = f"{idx_count}I"
        indices_bytes = struct.pack(indices_format, *self.indices)
        data_len = len(self.data)
        header_format = f"H Q H H H"
        header_size = struct.calcsize(header_format)

        fmt = f"{header_size}s {sid_len}s {idx_count}I I {data_len}s"
        packed_header = struct.pack(
            "H Q H H H",
            sid_len,
            self.droplet_id,
            self.degree,
            self.total_chunks,
            idx_count,
        )
        return struct.pack(
            f"{len(packed_header)}s {sid_len}s {idx_count}I I {data_len}s",
            packed_header,
            sid_bytes,
            *self.indices,
            data_len,
            self.data,
        )

    @classmethod
    def deserialize(cls, raw: bytes) -> Droplet:
        header_format = "H Q H H H"
        header_size = struct.calcsize(header_format)
        sid_len, droplet_id, degree, total_chunks, idx_count = struct.unpack_from(header_format, raw, 0)
        offset = header_size

        sid_bytes = raw[offset : offset + sid_len]
        session_id = sid_bytes.decode("utf-8")
        offset += sid_len

        indices_format = f"{idx_count}I"
        indices_size = struct.calcsize(indices_format)
        indices = list(struct.unpack_from(indices_format, raw, offset))
        offset += indices_size

        data_len = struct.unpack_from("I", raw, offset)[0]
        offset += 4

        data = raw[offset : offset + data_len]
        return cls(
            session_id=session_id,
            droplet_id=droplet_id,
            degree=degree,
            indices=indices,
            data=data,
            total_chunks=total_chunks,
        )


class LubyTransformEncoder:
    """Encodes raw state bytes into rateless Luby Transform fountain droplets."""

    def __init__(self, data: bytes, config: Optional[FountainConfig] = None) -> None:
        self.config = config or FountainConfig()
        self.data = data
        self.chunk_size = self.config.chunk_size
        self.chunks = self._split_into_chunks()
        self.k = len(self.chunks)
        self._lock = threading.Lock()
        self._next_id = 0

    def _split_into_chunks(self) -> List[bytes]:
        chunks = []
        for i in range(0, max(1, len(self.data)), self.chunk_size):
            chunk = self.data[i : i + self.chunk_size]
            # Pad last chunk if needed
            if len(chunk) < self.chunk_size:
                chunk = chunk + b"\x00" * (self.chunk_size - len(chunk))
            chunks.append(chunk)
        if not chunks:
            chunks.append(b"\x00" * self.chunk_size)
        return chunks

    def _sample_degree(self, rng: random.Random) -> int:
        # Robust Soliton distribution approximation or bounded random degree
        d = rng.randint(1, min(self.k, self.config.max_degree))
        return d

    def generate_droplet(self, session_id: str, seed: Optional[int] = None) -> Droplet:
        with self._lock:
            droplet_id = self._next_id
            self._next_id += 1

        rng = random.Random(seed if seed is not None else (droplet_id ^ hash(session_id)))
        degree = self._sample_degree(rng)
        indices = rng.sample(range(self.k), min(self.k, degree))
        indices.sort()

        # XOR the selected source chunks together
        combined = bytearray(self.chunk_size)
        for idx in indices:
            chunk = self.chunks[idx]
            for i in range(self.chunk_size):
                combined[i] ^= chunk[i]

        return Droplet(
            session_id=session_id,
            droplet_id=droplet_id,
            degree=len(indices),
            indices=indices,
            data=bytes(combined),
            total_chunks=self.k,
        )


class LubyTransformDecoder:
    """Decodes and reconstructs raw state from received fountain droplets using Gaussian elimination."""

    def __init__(self, total_chunks: int, chunk_size: Optional[int] = None) -> None:
        self.k = total_chunks
        self.chunk_size = chunk_size or 1024
        self._droplets: List[Droplet] = []
        self._lock = threading.Lock()
        self._solved = False
        self._reconstructed_data: Optional[bytes] = None

    def add_droplet(self, droplet: Droplet) -> bool:
        with self._lock:
            if self._solved:
                return True
            self._droplets.append(droplet)
            if len(self._droplets) >= self.k:
                success = self._attempt_reconstruction()
                if success:
                    self._solved = True
                    return True
            return False

    def is_complete(self) -> bool:
        with self._lock:
            return self._solved

    def _attempt_reconstruction(self) -> bool:
        # Simple belief propagation / triangularization decoder over GF(2)
        # Build system of equations: rows = droplets, cols = chunks
        matrix: List[List[int]] = []
        rhs: List[bytearray] = []

        for d in self._droplets:
            row = [0] * self.k
            for idx in d.indices:
                if idx < self.k:
                    row[idx] = 1
            matrix.append(row)
            rhs.append(bytearray(d.data))

        # Gaussian elimination to upper triangular or diagonal form
        nrows = len(matrix)
        for col in range(self.k):
            # Find pivot
            pivot_row = -1
            for r in range(col, nrows):
                if matrix[r][col] == 1:
                    pivot_row = r
                    break
            if pivot_row == -1:
                continue

            # Swap rows
            matrix[col], matrix[pivot_row] = matrix[pivot_row], matrix[col]
            rhs[col], rhs[pivot_row] = rhs[pivot_row], rhs[col]

            # Eliminate other rows
            for r in range(nrows):
                if r != col and matrix[r][col] == 1:
                    for c in range(col, self.k):
                        matrix[r][c] ^= matrix[col][c]
                    for b_idx in range(self.chunk_size):
                        rhs[r][b_idx] ^= rhs[col][b_idx]

        # Check if fully solved
        chunks: Dict[int, bytes] = {}
        for r in range(min(nrows, self.k)):
            ones = [c for c in range(self.k) if matrix[r][c] == 1]
            if len(ones) == 1:
                chunks[ones[0]] = bytes(rhs[r])

        if len(chunks) == self.k:
            ordered_chunks = [chunks[i] for i in range(self.k)]
            self._reconstructed_data = b"".join(ordered_chunks)
            return True

        return False

    def get_reconstructed_data(self) -> Optional[bytes]:
        with self._lock:
            return self._reconstructed_data


@dataclass
class TreeNode:
    node_id: str
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)
    is_leaf: bool = True


class HierarchicalAggregationTree:
    """Constructs and manages dynamic two-phase aggregation routing trees across cluster peers."""

    def __init__(self, root_id: str, peers: List[str], fanout: int = 4) -> None:
        self.root_id = root_id
        self.peers = sorted(list(set([root_id] + peers)))
        self.fanout = max(1, fanout)
        self.tree: Dict[str, TreeNode] = {}
        self._build_tree()

    def _build_tree(self) -> None:
        for p in self.peers:
            self.tree[p] = TreeNode(node_id=p)

        queue = [self.root_id]
        peer_idx = 0
        all_nodes = [p for p in self.peers if p != self.root_id]

        while queue and peer_idx < len(all_nodes):
            curr_id = queue.pop(0)
            curr_node = self.tree[curr_id]

            assigned = 0
            while assigned < self.fanout and peer_idx < len(all_nodes):
                child_id = all_nodes[peer_idx]
                curr_node.children.append(child_id)
                self.tree[child_id].parent = curr_id
                self.tree[child_id].is_leaf = False  # temporarily set non-leaf, checked later
                queue.append(child_id)
                peer_idx += 1
                assigned += 1

        # Refine leaf flags
        for node_id, node in self.tree.items():
            node.is_leaf = len(node.children) == 0

    def get_node(self, node_id: str) -> Optional[TreeNode]:
        return self.tree.get(node_id)

    def get_path_to_root(self, node_id: str) -> List[str]:
        path = []
        curr = node_id
        while curr and curr in self.tree:
            path.append(curr)
            curr = self.tree[curr].parent
        return path


class TwoPhaseGossipAggregator:
    """Orchestrates Phase 1 (bottom-up aggregation tree collection) and Phase 2 (top-down fountain broadcast)."""

    def __init__(self, node_id: str, peers: List[str], config: Optional[FountainConfig] = None) -> None:
        self.node_id = node_id
        self.peers = peers
        self.config = config or FountainConfig()
        self.tree = HierarchicalAggregationTree(root_id=node_id, peers=peers, fanout=self.config.tree_fanout)
        self._state_store: Dict[str, bytes] = {}
        self._decoders: Dict[str, LubyTransformDecoder] = {}
        self._lock = threading.Lock()

    def phase1_aggregate_up(self, session_id: str, local_state: bytes) -> Dict[str, bytes]:
        """Simulates bottom-up aggregation of child states towards parent nodes."""
        with self._lock:
            self._state_store[session_id] = local_state
            node = self.tree.get_node(self.node_id)
            if not node:
                return {self.node_id: local_state}

            # Aggregate child states if any
            aggregated = bytearray(local_state)
            for child_id in node.children:
                child_state = self._state_store.get(child_id, b"")
                # Simple XOR or concatenation combination for aggregation demo
                for i in range(min(len(aggregated), len(child_state))):
                    aggregated[i] ^= child_state[i]

            return {self.node_id: bytes(aggregated)}

    def phase2_disseminate_down(self, session_id: str, state_snapshot: bytes) -> List[Droplet]:
        """Encodes top-down state snapshot into fountain droplets for tree propagation."""
        encoder = LubyTransformEncoder(state_snapshot, self.config)
        num_droplets = int(encoder.k * self.config.overhead_factor) + 2
        droplets = [encoder.generate_droplet(session_id, seed=i) for i in range(num_droplets)]
        return droplets

    def receive_droplet(self, droplet: Droplet) -> bool:
        with self._lock:
            if droplet.session_id not in self._decoders:
                self._decoders[droplet.session_id] = LubyTransformDecoder(droplet.total_chunks, self.config.chunk_size)
            decoder = self._decoders[droplet.session_id]
            return decoder.add_droplet(droplet)

    def get_reconstructed_state(self, session_id: str) -> Optional[bytes]:
        with self._lock:
            decoder = self._decoders.get(session_id)
            if decoder and decoder.is_complete():
                return decoder.get_reconstructed_state()
            return None
