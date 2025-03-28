import asyncio
import argparse
import json
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import OpenAI


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai = OpenAI()

    async def connect_to_sse_server(self, server_url: str):
        """Connect to an MCP server running with SSE transport"""

        self._streams_context = sse_client(url=server_url)
        streams = await self._streams_context.__aenter__()

        self._session_context = ClientSession(*streams)
        self.session: ClientSession = await self._session_context.__aenter__()

        await self.session.initialize()

        print("Initialized SSE client...")
        print("Listing tools...")
        response = await self.session.list_tools()

        self.tools = response.tools

        print("")
        print("Connected")
        print("Tools:", [tool.name for tool in self.tools])

    async def cleanup(self):
        """Properly clean up the session and streams"""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

    def convert_tool_to_openai_function(self, tools):
        """Convert MCP tools schema into OpenAI function schema"""

        new_tools = []
        for tool in tools:
            new_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": False
                    },
                    "strict": True
                }
            }

            for key, value in tool.inputSchema['properties'].items():
                new_tool['function']['parameters']['properties'][key] = {
                    "type": value.get('type', 'string'),
                    "description": value.get('title', '')
                }
                
                new_tool['function']['parameters']['required'].append(key)

            new_tools.append(new_tool)

        return new_tools

    async def process_query(self, query: str) -> str:
        """Process a query using OpenAI and available tools"""

        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        mcp_tools = await self.session.list_tools()
        tools = self.convert_tool_to_openai_function(mcp_tools.tools)

        resp = self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools
        )

        assistant_msg = resp.choices[0].message
        if hasattr(assistant_msg, 'tool_calls') and assistant_msg.tool_calls:
            for tool_call in assistant_msg.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                tool_resp = await self.session.call_tool(function_name, function_args)
                _ = self.openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "assistant",
                            "content": f"response of tool call: {tool_resp.content[0].text}",
                        },
                   ],
                )
               
                return f'{tool_resp.content[0].text}'

        elif assistant_msg.content:
            response_text = assistant_msg.content
            return response_text
                

    async def chat_loop(self):
        print("\nAsk anything or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nYou: ").strip()
                if query.lower() == 'quit':
                    break
                    
                resp = await self.process_query(query)
                print("\n" + resp)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")


async def main():
    parser = argparse.ArgumentParser(description='MCP Client')
    parser.add_argument(
        '--address',
        type=str,
        help='MCP server address (i.e. http://localhost:8080/sse)')

    args = parser.parse_args()
    server_url = args.address

    client = MCPClient()
    try:
        await client.connect_to_sse_server(server_url=server_url)
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
