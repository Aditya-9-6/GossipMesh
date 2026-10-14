from typing import Dict, Callable


class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, Callable] = {}

    def register(self, name: str, handler: Callable):
        """Registers a new agent handler function by name."""
        if name in self._agents:
            raise ValueError(f"Agent {name} is already registered.")
        self._agents[name] = handler

    def get_agent(self, name: str) -> Callable:
        """Retrieves an agent handler function by name."""
        if name not in self._agents:
            raise ValueError(f"Agent {name} not found in registry.")
        return self._agents[name]

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())


# Global registry instance
agent_registry = AgentRegistry()
