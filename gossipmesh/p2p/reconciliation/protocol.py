from typing import Set, Tuple, Dict, Any, Optional, List
from gossipmesh.p2p.reconciliation.iblt import InvertibleBloomLookupTable

class IBLTReconciliationProtocol:
    def __init__(self, size: int = 80, num_hashes: int = 4, value_size: int = 32):
        self.size = size
        self.num_hashes = num_hashes
        self.value_size = value_size

    def create_iblt(self, inventory: Dict[int, bytes]) -> InvertibleBloomLookupTable:
        iblt = InvertibleBloomLookupTable(self.size, self.num_hashes, self.value_size)
        for k, v in inventory.items():
            iblt.insert(k, v)
        return iblt

    def reconcile(
        self, 
        local_inventory: Dict[int, bytes], 
        remote_iblt_data: dict
    ) -> Tuple[Set[Tuple[int, bytes]], Set[Tuple[int, bytes]], bool]:
        local_iblt = self.create_iblt(local_inventory)
        remote_iblt = InvertibleBloomLookupTable.deserialize(remote_iblt_data)
        
        diff_iblt = local_iblt.subtract(remote_iblt)
        added, removed, success = diff_iblt.list_entries()
        return added, removed, success

    def fallback_full_sync(self, local_inventory: Dict[int, bytes], remote_keys: List[int]) -> Dict[int, bytes]:
        missing = {}
        remote_set = set(remote_keys)
        for k, v in local_inventory.items():
            if k not in remote_set:
                missing[k] = v
        return missing
