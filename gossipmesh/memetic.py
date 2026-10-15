"""
Memetic Knowledge Distillation Engine.
Treats architectural patterns as evolving "Memes" with dynamic fitness scores.
Survivors of evolutionary natural selection are injected into LLM system prompts.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any

class KnowledgeMeme:
    def __init__(
        self,
        meme_id: str,
        title: str,
        rule: str,
        anti_pattern: str,
        correct_pattern: str,
        repo: str = "global",
        fitness_score: float = 1.0,
        successful_applications: int = 0,
        failed_applications: int = 0,
    ):
        self.meme_id = meme_id
        self.title = title
        self.rule = rule
        self.anti_pattern = anti_pattern
        self.correct_pattern = correct_pattern
        self.repo = repo
        self.fitness_score = fitness_score
        self.successful_applications = successful_applications
        self.failed_applications = failed_applications

    def reward(self, delta: float = 1.0):
        """Increases fitness when an applied meme results in an approved, merged PR."""
        self.fitness_score += delta
        self.successful_applications += 1

    def penalize(self, delta: float = 2.0):
        """Decreases fitness when an applied meme causes a review rejection or CI break."""
        self.fitness_score = max(0.0, self.fitness_score - delta)
        self.failed_applications += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "meme_id": self.meme_id,
            "title": self.title,
            "rule": self.rule,
            "anti_pattern": self.anti_pattern,
            "correct_pattern": self.correct_pattern,
            "repo": self.repo,
            "fitness_score": round(self.fitness_score, 2),
            "successful_applications": self.successful_applications,
            "failed_applications": self.failed_applications,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeMeme":
        return cls(
            meme_id=data["meme_id"],
            title=data["title"],
            rule=data["rule"],
            anti_pattern=data["anti_pattern"],
            correct_pattern=data["correct_pattern"],
            repo=data.get("repo", "global"),
            fitness_score=data.get("fitness_score", 1.0),
            successful_applications=data.get("successful_applications", 0),
            failed_applications=data.get("failed_applications", 0),
        )

class MemeticKnowledgeBase:
    """Persistent ledger of evolving architectural memes."""
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("G:/My Drive/.gossip_mesh/memes.json")
        self.memes: Dict[str, KnowledgeMeme] = {}
        self._load()

        # Seed foundational high-fitness patterns if empty
        if not self.memes:
            self._seed_defaults()

    def _load(self):
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                for m in data:
                    meme = KnowledgeMeme.from_dict(m)
                    self.memes[meme.meme_id] = meme
            except Exception:
                pass

    def save(self):
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            serializable = [m.to_dict() for m in self.memes.values()]
            self.storage_path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _seed_defaults(self):
        """Seeds initial verified architectural invariants."""
        seeds = [
            KnowledgeMeme(
                meme_id="go_lockfree_latency_buckets",
                title="Lock-Free Atomic Latency Tracking",
                rule="NEVER use sync.RWMutex or global locks on hot request latency paths.",
                anti_pattern="Using sync.RWMutex and make([]Duration) inside latency recording hot path.",
                correct_pattern="Use fixed [1000]atomic.Uint64 buckets with atomic.Add for O(1) lock-free recording.",
                repo="DevProxy",
                fitness_score=5.0,
            ),
            KnowledgeMeme(
                meme_id="go_zero_alloc_reporting",
                title="Zero-Allocation Percentile Reporting",
                rule="Avoid slice copies or heap allocations inside metric reporting methods.",
                anti_pattern="Allocating new slices with make([]Duration, len) inside GetPercentiles().",
                correct_pattern="Calculate percentiles by iterating over pre-allocated bucket counts directly.",
                repo="DevProxy",
                fitness_score=4.5,
            ),
            KnowledgeMeme(
                meme_id="rust_simd_json_in_place",
                title="SIMD-JSON Zero-Copy In-Place Parsing",
                rule="Use simd-json borrowed slices and in-place DOM inspection for WAF payloads.",
                anti_pattern="Converting raw byte buffers into owned String or serde_json::Value on hot paths.",
                correct_pattern="Use simd_json::to_borrowed_value(&mut bytes) and operate on byte slices.",
                repo="spryzen",
                fitness_score=5.0,
            ),
            KnowledgeMeme(
                meme_id="wireguard_mtu_probe_binary_search",
                title="WireGuard MTU Binary Search Prober",
                rule="Bound MTU discovery between 1280 and 1500 using binary search.",
                anti_pattern="Linear decrement of MTU by 1 byte per probe.",
                correct_pattern="Binary search mid-points (min_mtu + current_mtu) / 2 upon fragmentation.",
                repo="spryzen",
                fitness_score=4.0,
            )
        ]
        for s in seeds:
            self.memes[s.meme_id] = s
        self.save()

    def record_or_update(
        self,
        meme_id: str,
        title: str,
        rule: str,
        anti_pattern: str,
        correct_pattern: str,
        repo: str = "global"
    ) -> KnowledgeMeme:
        if meme_id in self.memes:
            m = self.memes[meme_id]
            m.title = title
            m.rule = rule
            m.anti_pattern = anti_pattern
            m.correct_pattern = correct_pattern
            m.repo = repo
        else:
            m = KnowledgeMeme(meme_id, title, rule, anti_pattern, correct_pattern, repo=repo)
            self.memes[meme_id] = m
        self.save()
        return m

    def reward(self, meme_id: str, delta: float = 1.0):
        if meme_id in self.memes:
            self.memes[meme_id].reward(delta)
            self.save()

    def penalize(self, meme_id: str, delta: float = 2.0):
        if meme_id in self.memes:
            self.memes[meme_id].penalize(delta)
            self.save()

    def get_top_memes(self, repo: str = "global", min_fitness: float = 1.0, limit: int = 10) -> List[KnowledgeMeme]:
        """Returns surviving high-fitness memes for prompt injection, filtered by repo."""
        candidates = [
            m for m in self.memes.values()
            if m.fitness_score >= min_fitness and (m.repo == repo or m.repo == "global" or repo == "global")
        ]
        candidates.sort(key=lambda m: m.fitness_score, reverse=True)
        return candidates[:limit]

    def format_prompt_context(self, repo: str = "global") -> str:
        """Formats the top memes into Markdown for direct LLM system prompt injection."""
        top = self.get_top_memes(repo=repo, limit=8)
        if not top:
            return ""

        lines = ["### 🧬 GOSSIPED ARCHITECTURAL MEMES & HARD INVARIANTS:"]
        for m in top:
            lines.append(f"- **{m.title}** (Fitness: {m.fitness_score}★)")
            lines.append(f"  • Directive: {m.rule}")
            lines.append(f"  • Anti-Pattern To Avoid: {m.anti_pattern}")
            lines.append(f"  • Required Pattern: {m.correct_pattern}")
        return "\n".join(lines)
