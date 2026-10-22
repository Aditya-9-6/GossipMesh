import sys
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from gossipmesh.cli import (
    cmd_status,
    cmd_broadcast,
    cmd_memes,
    cmd_audit,
    main
)

@pytest.fixture
def mock_args():
    args = MagicMock()
    args.mesh_dir = "/tmp/mesh"
    args.node_id = "test_node"
    args.topic = "test_topic"
    args.message = "hello"
    args.repo = "test_repo"
    args.path = "test_file.py"
    return args

@patch("gossipmesh.cli.MemeticKnowledgeBase")
@patch("gossipmesh.cli.GossipNode")
def test_cmd_status_no_heartbeats(mock_gossip_node, mock_mkb, mock_args, capsys):
    mock_node_instance = mock_gossip_node.return_value
    mock_node_instance.mesh_dir = "/tmp/mesh"
    mock_node_instance.log_file.exists.return_value = False
    mock_node_instance.heartbeats_file.exists.return_value = False

    mock_mkb_instance = mock_mkb.return_value
    mock_mkb_instance.get_top_memes.return_value = []

    cmd_status(mock_args)

    captured = capsys.readouterr()
    assert "GOSSIPMESH: P2P MULTI-AGENT MESH STATUS" in captured.out
    assert "(No heartbeat ledger initialized)" in captured.out

@patch("gossipmesh.cli.MemeticKnowledgeBase")
@patch("gossipmesh.cli.GossipNode")
def test_cmd_status_with_heartbeats(mock_gossip_node, mock_mkb, mock_args, capsys):
    mock_node_instance = mock_gossip_node.return_value
    mock_node_instance.mesh_dir = "/tmp/mesh"
    mock_node_instance.log_file.exists.return_value = True
    mock_node_instance.heartbeats_file.exists.return_value = True
    mock_node_instance.heartbeats_file.read_text.return_value = json.dumps({
        "node_1": {"last_seen": 12345.0, "clock_seq": 1}
    })

    mock_mkb_instance = mock_mkb.return_value
    meme = MagicMock()
    meme.fitness_score = 9.5
    meme.title = "Test Meme"
    meme.repo = "test_repo"
    meme.rule = "Always test"
    mock_mkb_instance.get_top_memes.return_value = [meme]

    cmd_status(mock_args)

    captured = capsys.readouterr()
    assert "node_1" in captured.out
    assert "Test Meme" in captured.out

@patch("gossipmesh.cli.GossipNode")
def test_cmd_broadcast(mock_gossip_node, mock_args, capsys):
    mock_node_instance = mock_gossip_node.return_value
    mock_msg = MagicMock()
    mock_msg.message_id = "msg123"
    mock_node_instance.publish.return_value = mock_msg

    cmd_broadcast(mock_args)

    mock_node_instance.publish.assert_called_once_with(
        mock_args.topic, {"message": mock_args.message, "origin": "cli"}, repo=mock_args.repo
    )
    captured = capsys.readouterr()
    assert "[OK] Broadcasted gossip message 'msg123' on topic 'test_topic' across mesh." in captured.out

@patch("gossipmesh.cli.MemeticKnowledgeBase")
def test_cmd_memes(mock_mkb, mock_args, capsys):
    mock_mkb_instance = mock_mkb.return_value
    mock_mkb_instance.format_prompt_context.return_value = "Prompt context"

    cmd_memes(mock_args)

    mock_mkb_instance.format_prompt_context.assert_called_once_with(repo=mock_args.repo)
    captured = capsys.readouterr()
    assert "Prompt context\n" in captured.out

@patch("gossipmesh.cli.sys.exit")
@patch("gossipmesh.cli.Path")
@patch("gossipmesh.cli.RedTeamAuditor")
def test_cmd_audit_file_not_found(mock_auditor, mock_path_cls, mock_exit, mock_args, capsys):
    mock_path_instance = mock_path_cls.return_value
    mock_path_instance.exists.return_value = False

    cmd_audit(mock_args)

    mock_exit.assert_called_once_with(1)
    captured = capsys.readouterr()
    assert "[Error] File not found" in captured.out

@patch("gossipmesh.cli.Path")
@patch("gossipmesh.cli.RedTeamAuditor")
def test_cmd_audit_no_probes(mock_auditor, mock_path_cls, mock_args, capsys):
    mock_path_instance = mock_path_cls.return_value
    mock_path_instance.exists.return_value = True
    mock_path_instance.read_text.return_value = "code"
    mock_path_instance.name = "test_file.py"

    mock_auditor_instance = mock_auditor.return_value
    mock_auditor_instance.audit_diff.return_value = []

    cmd_audit(mock_args)

    captured = capsys.readouterr()
    assert "--- Red Team Adversarial Audit: test_file.py ---" in captured.out
    assert "[OK] No critical anti-patterns or race condition vulnerabilities detected." in captured.out

@patch("gossipmesh.cli.Path")
@patch("gossipmesh.cli.RedTeamAuditor")
def test_cmd_audit_with_probes(mock_auditor, mock_path_cls, mock_args, capsys):
    mock_path_instance = mock_path_cls.return_value
    mock_path_instance.exists.return_value = True
    mock_path_instance.read_text.return_value = "code"
    mock_path_instance.name = "test_file.py"

    probe = MagicMock()
    probe.severity = "CRITICAL"
    probe.category = "Security"
    probe.description = "SQL Injection"
    probe.attack_vector = "User input"
    probe.exploit_test_stub = "def test_exploit(): pass"

    mock_auditor_instance = mock_auditor.return_value
    mock_auditor_instance.audit_diff.return_value = [probe]

    cmd_audit(mock_args)

    captured = capsys.readouterr()
    assert "[CRITICAL] Security: SQL Injection" in captured.out
    assert "def test_exploit(): pass" in captured.out

@patch("gossipmesh.cli.sys.argv", ["gossipmesh", "status"])
@patch("gossipmesh.cli.cmd_status")
def test_main_status(mock_cmd_status):
    main()
    mock_cmd_status.assert_called_once()
    args = mock_cmd_status.call_args[0][0]
    assert args.command == "status"

@patch("gossipmesh.cli.sys.argv", ["gossipmesh", "broadcast", "--message", "hello"])
@patch("gossipmesh.cli.cmd_broadcast")
def test_main_broadcast(mock_cmd_broadcast):
    main()
    mock_cmd_broadcast.assert_called_once()
    args = mock_cmd_broadcast.call_args[0][0]
    assert args.command == "broadcast"
    assert args.message == "hello"

@patch("gossipmesh.cli.sys.argv", ["gossipmesh", "memes"])
@patch("gossipmesh.cli.cmd_memes")
def test_main_memes(mock_cmd_memes):
    main()
    mock_cmd_memes.assert_called_once()
    args = mock_cmd_memes.call_args[0][0]
    assert args.command == "memes"

@patch("gossipmesh.cli.sys.argv", ["gossipmesh", "audit", "test_file.py"])
@patch("gossipmesh.cli.cmd_audit")
def test_main_audit(mock_cmd_audit):
    main()
    mock_cmd_audit.assert_called_once()
    args = mock_cmd_audit.call_args[0][0]
    assert args.command == "audit"
    assert args.path == "test_file.py"
