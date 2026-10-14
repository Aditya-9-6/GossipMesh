"""
GossipMesh Command-Line Interface.
Manage peer nodes, inspect memetic knowledge, broadcast gossip, and audit diffs.
"""

import sys
import json
import argparse
from pathlib import Path
from .node import GossipNode, GossipTopic
from .memetic import MemeticKnowledgeBase
from .red_team import RedTeamAuditor

def cmd_status(args):
    node = GossipNode("cli_inspector", mesh_dir=args.mesh_dir)
    print("=" * 65)
    print("         GOSSIPMESH: P2P MULTI-AGENT MESH STATUS")
    print("=" * 65)
    print(f"Mesh Directory: {node.mesh_dir}")
    print(f"Ledger File:    {node.log_file} (Exists: {node.log_file.exists()})")

    # Read heartbeats
    hb_file = node.heartbeats_file
    print("\n--- Active Peer Nodes ---")
    if hb_file.exists():
        try:
            hb = json.loads(hb_file.read_text(encoding="utf-8"))
            for nid, data in hb.items():
                print(f"  * {nid:<24} | Last Seen: {data.get('last_seen', 0):.1f} | Clock: {data.get('clock_seq', 0)}")
        except Exception:
            print("  (No active heartbeats found)")
    else:
        print("  (No heartbeat ledger initialized)")

    kb = MemeticKnowledgeBase()
    top_memes = kb.get_top_memes()
    print(f"\n--- Top Memetic Knowledge Rules ({len(top_memes)} active) ---")
    for m in top_memes:
        print(f"  [{m.fitness_score:4.1f}*] {m.title:<35} ({m.repo})")
        print(f"         Rule: {m.rule}")

def cmd_broadcast(args):
    node = GossipNode(args.node_id or "cli_broadcaster", mesh_dir=args.mesh_dir)
    payload = {"message": args.message, "origin": "cli"}
    msg = node.publish(args.topic, payload, repo=args.repo)
    print(f"[OK] Broadcasted gossip message '{msg.message_id}' on topic '{args.topic}' across mesh.")

def cmd_memes(args):
    kb = MemeticKnowledgeBase()
    print(kb.format_prompt_context(repo=args.repo))

def cmd_audit(args):
    auditor = RedTeamAuditor()
    path = Path(args.path)
    if not path.exists():
        print(f"[Error] File not found: {path}")
        sys.exit(1)

    content = path.read_text(encoding="utf-8", errors="replace")
    probes = auditor.audit_diff(content)
    print(f"--- Red Team Adversarial Audit: {path.name} ---")
    if not probes:
        print("[OK] No critical anti-patterns or race condition vulnerabilities detected.")
    else:
        for p in probes:
            print(f"[{p.severity}] {p.category}: {p.description}")
            print(f"  Attack Vector: {p.attack_vector}")
            print(f"  Suggested Test:\n{p.exploit_test_stub}\n")

def main():
    parser = argparse.ArgumentParser(description="GossipMesh Multi-Agent Peer CLI")
    parser.add_argument("--mesh-dir", default=None, help="Custom mesh directory path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    subparsers.add_parser("status", help="Inspect active peers, heartbeats, and top memes")

    # broadcast
    p_bcast = subparsers.add_parser("broadcast", help="Publish a gossip event to the mesh")
    p_bcast.add_argument("--topic", default="best_practices", help="Gossip topic")
    p_bcast.add_argument("--message", required=True, help="Message content")
    p_bcast.add_argument("--repo", default="global", help="Target repository scope")
    p_bcast.add_argument("--node-id", default="cli_operator", help="Sender node ID")

    # memes
    p_memes = subparsers.add_parser("memes", help="Show formatted prompt context for top memes")
    p_memes.add_argument("--repo", default="global", help="Filter by repo")

    # audit
    p_audit = subparsers.add_parser("audit", help="Run Red Team adversarial audit on a code file")
    p_audit.add_argument("path", help="Path to code file")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status(args)
    elif args.command == "broadcast":
        cmd_broadcast(args)
    elif args.command == "memes":
        cmd_memes(args)
    elif args.command == "audit":
        cmd_audit(args)

if __name__ == "__main__":
    main()
