import json
import os

from mcp_local.client import MCPClient
from tools.external_search_mcp_tool import ExternalSearchMCPTool


class MCPManager:


    def __init__(
        self,
        config_path
    ):

        with open(
            config_path,
            "r",
            encoding="utf-8"
        ) as f:

            self.config = json.load(f)


        self.clients = {}
        self.tools = {}



    async def register(
        self,
        server_name
    ):

        config = self.config["servers"][server_name]


        env = {}

        # Runtime secret injection
        if server_name == "tavily":

            tavily_key = os.getenv(
                "TAVILY_API_KEY"
            )

            if tavily_key:
                env["TAVILY_API_KEY"] = tavily_key


        client = MCPClient(
            command=config["command"],
            args=config["args"],
            env=env
        )


        await client.connect()


        self.clients[server_name] = client


        if server_name == "tavily":

            self.tools["tavily"] = ExternalSearchMCPTool(
                client
            )



    def get_tool(
        self,
        name
    ):

        return self.tools[name]



    async def close(self):

        for client in self.clients.values():

            await client.close()