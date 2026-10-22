with open("tests/test_p2p_scatter.py", "r") as f:
    data = f.read()

data = data.replace(
    "recent = node.get_recent_messages(GossipTopic.AGENT_EVENT)",
    "recent = [m for m in node.recent_messages if m.topic == GossipTopic.AGENT_EVENT.value]",
)

with open("tests/test_p2p_scatter.py", "w") as f:
    f.write(data)
