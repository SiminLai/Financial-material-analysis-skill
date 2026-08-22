try:
    from mcp import ClientSession
    from mcp.client.stdio import (
        stdio_client,
        StdioServerParameters
    )

    class MCPClient:

        def __init__(
            self,
            command,
            args=None,
            env=None
        ):

            self.command = command
            self.args = args or []
            self.env = env or {}

            self.session = None

            self._stdio_context = None
            self._session_context = None

        async def connect(self):

            print("COMMAND:", self.command)
            print("ARGS:", self.args)

            server_params = StdioServerParameters(
                command=self.command,
                args=self.args,
                env=self.env
            )

            self._stdio_context = stdio_client(server_params)

            read, write = await self._stdio_context.__aenter__()

            self._session_context = ClientSession(read, write)

            await self._session_context.__aenter__()

            await self._session_context.initialize()

            self.session = self._session_context

            tools = await self.session.list_tools()

            print("\n===== MCP AVAILABLE TOOLS =====")

            for tool in tools.tools:
                print(f"- {tool.name}")
                print(f"  description: {tool.description}")

            print("===============================\n")

        async def close(self):

            if self._session_context:
                await self._session_context.__aexit__(None, None, None)

            if self._stdio_context:
                await self._stdio_context.__aexit__(None, None, None)

        async def call_tool(self, name, arguments):
            return await self.session.call_tool(name=name, arguments=arguments)

except Exception:

    class MCPClient:

        def __init__(self, command, args=None, env=None):
            self.command = command
            self.args = args or []
            self.env = env or {}
            self.session = None

        async def connect(self):
            print("MCP package not installed; MCP client disabled.")

        async def close(self):
            return

        async def call_tool(self, name, arguments):
            raise RuntimeError("MCP client not available")