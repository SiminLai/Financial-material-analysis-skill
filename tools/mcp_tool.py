from typing import Any

from .base_tool import BaseTool


class MCPTool(BaseTool):
    """
    Base class for tools powered by MCP protocol.
    """

    def __init__(self, client: Any):
        if client is None:
            raise ValueError(
                "MCP client must not be None"
            )

        self.client = client


    async def call_mcp(
        self,
        tool_name: str,
        arguments: dict
    ):

        return await self.client.call_tool(
            tool_name,
            arguments
        )