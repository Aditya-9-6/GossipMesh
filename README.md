# GossipMesh 🌐

> **Decentralized P2P Gossip Protocol Multi-Agent Autonomous Engineering Mesh**  
> *Enabling autonomous software engineering agents to cross-pollinate architectural wisdom, prevent repeated mistakes, enforce Byzantine quorum consensus, and maintain cross-repository wire compatibility.*

---

## 🌟 Overview

In traditional multi-agent systems, agents operate as isolated silos: issue generators don't know why previous PRs failed, solvers repeat past anti-patterns, and different repositories (e.g. Go network proxies and Rust Zero-Trust VPNs) suffer from protocol drift.

**GossipMesh** introduces a peer-to-peer epidemic knowledge protocol for autonomous coding agents. Agents continuously disseminate discoveries, dynamic architectural memes, adversarial stress probes, and benchmark invariants across decentralized nodes.

```mermaid
graph TD
    subgraph Gossip Mesh Ledger
        GL[Append-Only Gossip Ledger & Vector Clocks]
    end

    subgraph DevProxy Cluster (Go)
        D_GEN[Issue Generator Node] -->|Sync Memes| GL
        D_SOLV[Solver Node] -->|Broadcast Findings| GL
        D_REV[Reviewer Node] -->|Gossip Anti-Patterns| GL
    end

    subgraph Spryzen Cluster (Rust)
        S_GEN[Architect Node] -->|Sync Wire Schemas| GL
        S_SOLV[Solver Node] -->|Broadcast Benchmarks| GL
        S_REV[Reviewer Node] -->|Vote Quorum| GL
    end

    subgraph Autonomous Peers
        RED[Red Team Adversarial Fuzzer] -->|Exploit Probes| GL
        ORACLE[Zero-Allocation Perf Oracle] -->|Telemetry Veto| GL
        AUCTION[Contract Net Auctioneer] -->|Task Allocation| GL
    end
```

---

## 🚀 Key Advancements

### 1. Epidemic Anti-Entropy Gossip Dissemination (`gossipmesh.node`)
- Peer nodes exchange cryptographically verified messages with **vector clocks** and **time-to-live (TTL)** counters.
- Automatic anti-entropy synchronization catches up lagging nodes whenever they cycle.

### 2. Memetic Knowledge Distillation (`gossipmesh.memetic`)
- Treats architectural rules as evolving **Memes** with dynamic **fitness scores**:
  - PR approved & merged ($\ge 90/100$ score): Meme rewarded (`fitness += 1.0`).
  - PR rejected / CI break: Meme penalized (`fitness -= 2.0`).
- The mesh runs **evolutionary natural selection**, pruning bad advice and prioritizing battle-tested invariants in LLM prompt headers.

### 3. Heterogeneous Multi-Model Byzantine Consensus (`gossipmesh.consensus`)
- Cross-audits proposed code changes across multiple model tiers (`gemini-3.8-flash`, `gemini-3.1-pro-preview`, and `gemini-3.1-flash-lite`).
- Requires a **$2/3$ majority quorum** and minimum score threshold before allowing code to be pushed to GitHub.

### 4. Red Team vs. Blue Team Adversarial Auditing (`gossipmesh.red_team`)
- Adversarial peer inspects code diffs prior to PR creation.
- Probes for mutex bottlenecks on hot paths, unbounded heap allocations, out-of-bounds slicing, and path traversal vectors.

### 5. Cross-Repo Wire Contract Synchronizer (`gossipmesh.bridge`)
- Translates shared data structures between **Go** ([`DevProxy`](https://github.com/Aditya-9-6/DevProxy)) and **Rust** ([`Spryzen`](https://github.com/Aditya-9-6/spryzen)).
- Generates matching Go structs and Rust Serde types automatically to prevent protocol divergence.

### 6. Zero-Allocation Performance Regression Oracle (`gossipmesh.oracle`)
- Tracks time-series microbenchmark metrics (`ns/op`, `B/op`, `allocs/op`).
- Issues an immediate **VETO** if a proposed change introduces unexpected allocations on a zero-allocation hot path.

### 7. Contract Net Protocol Task Auction (`gossipmesh.auction`)
- Rather than naive sequential issue processing, advancement specifications are posted as RFQs.
- Specialized personas (*Concurrency*, *Security*, *Crypto*, *Systems*) submit competitive domain bids to select the optimal solver.

---

## 💻 CLI Usage

```bash
# Check mesh status, active heartbeats, and top memetic knowledge
python -m gossipmesh.cli status

# Broadcast an architectural learning across all agent daemons
python -m gossipmesh.cli broadcast --topic anti_patterns --message "Use atomic buckets, avoid mutex on hot path" --repo DevProxy

# Inspect the formatted prompt injection context
python -m gossipmesh.cli memes --repo DevProxy

# Run the Red Team adversarial auditor on a code file
python -m gossipmesh.cli audit path/to/source.go
```

---

## 🧪 Testing

Run the comprehensive unit test suite:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## 📜 License

Apache-2.0 License. Built by [Aditya Dahale](https://github.com/Aditya-9-6).
