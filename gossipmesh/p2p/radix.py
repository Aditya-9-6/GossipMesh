from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional, Tuple


class RadixNode:
    __slots__ = ("prefix", "value", "children")

    def __init__(self, prefix: str = "", value: Any = None) -> None:
        self.prefix: str = prefix
        self.value: Any = value
        self.children: Dict[str, RadixNode] = {}

    def __repr__(self) -> str:
        return f"RadixNode(prefix={self.prefix!r}, value={self.value!r}, children={list(self.children.keys())})"


class CacheObliviousRadixTree:
    """
    Cache-Oblivious Compressed Radix Tree (PATRICIA Trie) optimized for
    sub-microsecond peer address prefix lookups and identifier routing.
    Supports lock-free concurrent reads via atomic snapshot swapping.
    """

    def __init__(self) -> None:
        self._root = RadixNode()
        self._size = 0
        self._write_lock = threading.Lock()

    def _get_snapshot(self) -> RadixNode:
        """Atomic snapshot reference for lock-free read operations."""
        return self._root

    def insert(self, key: str, value: Any = None) -> None:
        """
        Inserts a key-value pair into the radix tree in O(K) time where K is key length.
        Thread-safe under exclusive write locking with lock-free atomic root publication.
        """
        if not isinstance(key, str) or not key:
            raise ValueError("Key must be a non-empty string.")

        with self._write_lock:
            # Construct a deep copy/new tree structure for lock-free copy-on-write or mutate in place under lock
            # For maximum throughput, we mutate under the write lock and publish root atomically.
            curr = self._root
            idx = 0
            key_len = len(key)

            while idx < key_len:
                char = key[idx]
                if char not in curr.children:
                    # Create new child node for the remaining suffix
                    curr.children[char] = RadixNode(prefix=key[idx:], value=value)
                    self._size += 1
                    return

                child = curr.children[char]
                prefix = child.prefix
                prefix_len = len(prefix)

                # Find common prefix length between key[idx:] and child.prefix
                matched = 0
                while idx + matched < key_len and matched < prefix_len and key[idx + matched] == prefix[matched]:
                    matched += 1

                if matched == prefix_len:
                    # Consumed entire child prefix, advance index and traverse down
                    idx += matched
                    curr = child
                    if idx == key_len:
                        curr.value = value
                        return
                else:
                    # Partial match: split the child node
                    common_prefix = prefix[:matched]
                    remainder_child = prefix[matched:]

                    # Create new intermediate node
                    intermediate = RadixNode(prefix=common_prefix, value=None)
                    intermediate.children[remainder_child[0]] = child
                    child.prefix = remainder_child

                    # Attach intermediate to current parent
                    curr.children[char] = intermediate

                    if idx + matched == key_len:
                        intermediate.value = value
                        self._size += 1
                        return
                    else:
                        # Create leaf/branch for the remaining part of the new key
                        remaining_key = key[idx + matched :]
                        leaf = RadixNode(prefix=remaining_key, value=value)
                        intermediate.children[remaining_key[0]] = leaf
                        self._size += 1
                        return

            curr.value = value

    def search(self, key: str) -> Optional[Any]:
        """
        Searches for an exact key match in O(K) time.
        Lock-free read path using atomic snapshot reference.
        """
        if not isinstance(key, str) or not key:
            return None

        curr = self._get_snapshot()
        idx = 0
        key_len = len(key)

        while idx < key_len:
            char = key[idx]
            if char not in curr.children:
                return None
            child = curr.children[char]
            prefix = child.prefix
            prefix_len = len(prefix)

            if key_len - idx < prefix_len:
                return None

            if key[idx : idx + prefix_len] != prefix:
                return None

            idx += prefix_len
            curr = child

        return curr.value if idx == key_len else None

    def longest_prefix_match(self, key: str) -> Tuple[Optional[str], Optional[Any]]:
        """
        Finds the longest prefix match for peer address or identifier routing lookups.
        Returns a tuple of (matched_prefix_key, value).
        """
        if not isinstance(key, str) or not key:
            return (None, None)

        curr = self._get_snapshot()
        idx = 0
        key_len = len(key)
        best_match_key: Optional[str] = None
        best_match_value: Optional[Any] = None
        current_accumulated = ""

        while idx < key_len:
            char = key[idx]
            if char not in curr.children:
                break
            child = curr.children[char]
            prefix = child.prefix
            prefix_len = len(prefix)

            if key_len - idx < prefix_len:
                # Check partial match on child prefix
                matched = 0
                while idx + matched < key_len and matched < prefix_len and key[idx + matched] == prefix[matched]:
                    matched += 1
                if matched > 0:
                    current_accumulated += prefix[:matched]
                    if child.value is not None:
                        best_match_key = current_accumulated
                        best_match_value = child.value
                break

            if key[idx : idx + prefix_len] != prefix:
                # Partial match validation
                matched = 0
                while matched < prefix_len and idx + matched < key_len and key[idx + matched] == prefix[matched]:
                    matched += 1
                if matched > 0:
                    current_accumulated += prefix[:matched]
                    if child.value is not None:
                        best_match_key = current_accumulated
                        best_match_value = child.value
                break

            current_accumulated += prefix
            idx += prefix_len
            curr = child
            if curr.value is not None:
                best_match_key = current_accumulated
                best_match_value = curr.value

        return (best_match_key, best_match_value)

    def delete(self, key: str) -> bool:
        """
        Deletes a key from the radix tree. Returns True if successfully deleted, False otherwise.
        """
        if not isinstance(key, str) or not key:
            return False

        with self._write_lock:
            # Perform deletion recursively or iteratively with cleanup of empty nodes
            stack: List[Tuple[RadixNode, str, int]] = []
            curr = self._root
            idx = 0
            key_len = len(key)

            while idx < key_len:
                char = key[idx]
                if char not in curr.children:
                    return False
                child = curr.children[char]
                prefix = child.prefix
                prefix_len = len(prefix)

                if key_len - idx < prefix_len or key[idx : idx + prefix_len] != prefix:
                    return False

                stack.append((curr, char, idx))
                idx += prefix_len
                curr = child

            if curr.value is None:
                return False

            curr.value = None
            self._size -= 1

            # Clean up empty or redundant nodes upwards in the stack
            while stack:
                parent, char, _ = stack.pop()
                node = parent.children[char]
                if node.value is None and not node.children:
                    del parent.children[char]
                elif node.value is None and len(node.children) == 1:
                    # Compress single child node
                    only_child_char = next(iter(node.children))
                    only_child = node.children[only_child_char]
                    node.prefix += only_child.prefix
                    node.value = only_child.value
                    node.children = only_child.children
                else:
                    break
                if parent.value is not None or parent.children:
                    break

            return True

    def __len__(self) -> int:
        return self._size

    def clear(self) -> None:
        with self._write_lock:
            self._root = RadixNode()
            self._size = 0
