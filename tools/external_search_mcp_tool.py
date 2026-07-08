from typing import Any

from .mcp_tool import MCPTool


class ExternalSearchMCPTool(MCPTool):

    name = "browser_search"

    description = """
    Retrieve external knowledge from web sources
    """

    input_schema = {
        "type": "dict",
        "required_fields": [
            "query"
        ],
        "field_types": {
            "query": str
        }
    }


    async def _aexecute(
        self,
        input_data: Any
    ):

        query = input_data["query"]

        result = await self.call_mcp(
            tool_name="tavily_search",
            arguments={
                "query": query
            }
        )


        return {
            "text": result.content[0].text
        }