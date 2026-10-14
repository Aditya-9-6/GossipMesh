
with open("gossipmesh/providers/openai_adapter.py", "r") as f:
    content = f.read()

content = content.replace("formatted_messages = [{\"role\": msg.role, \"content\": msg.content} for msg in request.messages]", "formatted_messages: list[Any] = [{\"role\": msg.role, \"content\": msg.content} for msg in request.messages]")

content = content.replace("            prompt_tokens=response.usage.prompt_tokens,\n            completion_tokens=response.usage.completion_tokens,\n            total_tokens=response.usage.total_tokens,", "            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,\n            completion_tokens=response.usage.completion_tokens if response.usage else 0,\n            total_tokens=response.usage.total_tokens if response.usage else 0,")

content = content.replace("        stream = await self.client.chat.completions.create(", "        stream: Any = await self.client.chat.completions.create(")
content = "from typing import Any\n" + content

with open("gossipmesh/providers/openai_adapter.py", "w") as f:
    f.write(content)
