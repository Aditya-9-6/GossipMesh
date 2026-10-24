from typing import Dict, Any
from gossipmesh.p2p.entropy import AntiEntropyScraper


class MeshSyncer:
    def __init__(self, scraper: Optional[AntiEntropyScraper] = None):
        self.scraper = scraper or AntiEntropyScraper()

    def sync_node(self, peer_id: str, local_clock: Dict[str, int]) -> bool:
        self.scraper.scan_mesh(local_clock)
        return True
