import time
import asyncio
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from gossipmesh.consensus.state_machine import StateMachine


class RaftState(str, Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class LogEntry:
    def __init__(self, term: int, index: int, command: Dict[str, Any]):
        self.term = term
        self.index = index
        self.command = command

    def to_dict(self) -> Dict[str, Any]:
        return {"term": self.term, "index": self.index, "command": self.command}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogEntry":
        return cls(term=data["term"], index=data["index"], command=data["command"])


class RaftNode:
    """Quorum-Based Epoch-Locked Raft Node for decentralized multi-agent synchronization."""

    def __init__(self, node_id: str, peers: List[str]):
        self.node_id = node_id
        self.peers = peers
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.log: List[LogEntry] = []
        self.state = RaftState.FOLLOWER
        self.commit_index = 0
        self.last_applied = 0

        # Leader state
        self.next_index: Dict[str, int] = {}
        self.match_index: Dict[str, int] = {}

        self.state_machine = StateMachine()
        self.last_heartbeat = time.time()
        self.election_timeout = 0.15 + (hash(node_id) % 100) / 1000.0
        self._running = False

    def get_last_log_term_and_index(self) -> Tuple[int, int]:
        if not self.log:
            return (0, 0)
        last = self.log[-1]
        return (last.term, last.index)

    def request_vote(self, term: int, candidate_id: str, last_log_term: int, last_log_index: int) -> Dict[str, Any]:
        """Handle incoming RequestVote RPC."""
        if term > self.current_term:
            self.current_term = term
            self.state = RaftState.FOLLOWER
            self.voted_for = None

        grant = False
        if term == self.current_term and (self.voted_for is None or self.voted_for == candidate_id):
            my_last_term, my_last_index = self.get_last_log_term_and_index()
            up_to_date = (
                last_log_term > my_last_term
                or (last_log_term == my_last_term and last_log_index >= my_last_index)
            )
            if up_to_date:
                grant = True
                self.voted_for = candidate_id
                self.last_heartbeat = time.time()

        return {"term": self.current_term, "vote_granted": grant}

    def append_entries(
        self, term: int, leader_id: str, prev_log_index: int, prev_log_term: int, entries: List[Dict[str, Any]], leader_commit: int
    ) -> Dict[str, Any]:
        """Handle incoming AppendEntries RPC and heartbeats."""
        if term < self.current_term:
            return {"term": self.current_term, "success": False}

        if term > self.current_term or self.state == RaftState.CANDIDATE:
            self.current_term = term
            self.state = RaftState.FOLLOWER
            self.voted_for = None

        self.last_heartbeat = time.time()

        # Check previous log index consistency
        if prev_log_index > 0:
            if len(self.log) < prev_log_index or self.log[prev_log_index - 1].term != prev_log_term:
                return {"term": self.current_term, "success": False}

        # Append any new entries not already in the log
        for i, entry_data in enumerate(entries):
            entry = LogEntry.from_dict(entry_data)
            idx = prev_log_index + 1 + i
            if idx <= len(self.log):
                if self.log[idx - 1].term != entry.term:
                    self.log = self.log[:idx - 1]
                    self.log.append(entry)
            else:
                self.log.append(entry)

        # Update commit index
        if leader_commit > self.commit_index:
            self.commit_index = min(leader_commit, len(self.log))
            self._apply_committed_entries()

        return {"term": self.current_term, "success": True}

    def _apply_committed_entries(self):
        while self.commit_index > self.last_applied:
            self.last_applied += 1
            entry = self.log[self.last_applied - 1]
            self.state_machine.apply(entry.command)

    def start_election(self) -> Tuple[int, str, int, int]:
        """Transition to candidate state and return election ballot info."""
        self.state = RaftState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.last_heartbeat = time.time()
        last_term, last_index = self.get_last_log_term_and_index()
        return (self.current_term, self.node_id, last_term, last_index)

    def client_write(self, command: Dict[str, Any]) -> bool:
        """Propose a new command to the state machine if leader."""
        if self.state != RaftState.LEADER:
            return False
        index = len(self.log) + 1
        entry = LogEntry(term=self.current_term, index=index, command=command)
        self.log.append(entry)
        return True

    def compact_log(self, upto_index: int):
        """Bounded append-entries log compaction."""
        if upto_index > 0 and upto_index <= len(self.log):
            self.log = self.log[upto_index:]
