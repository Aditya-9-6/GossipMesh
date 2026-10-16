class Node:
    def __init__(self, node_id, ip, port):
        self.node_id = node_id
        self.ip = ip
        self.port = port

    def ping(self, remote_node):
        # Ping a remote node
        pass

    def handle_ping(self, sender, message):
        # Handle incoming ping message
        pass
