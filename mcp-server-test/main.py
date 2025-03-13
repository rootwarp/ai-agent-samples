import httpx
from mcp.server import Server
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.requests import Request
import uvicorn
import asyncio


mcp = FastMCP("anonymous")
rpc_endpoint = "https://ethereum.publicnode.com"


@mcp.tool()
async def get_balance(address: str) -> float:
    """
    Get the balance of an address on a network

    Args:
        address: The address to get the balance of

    Returns:
        The balance of the address on the network
    """

    async with httpx.AsyncClient() as client:
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getBalance",
            "params": [address, "latest"],
            "id": 1
        }
        headers = {'Content-type': 'application/json'}
        resp = await client.post(rpc_endpoint, json=payload, headers=headers)
        if resp.status_code != 200:
            raise ValueError(f"Error from Ethereum node: {resp.text}")

        try:
            data = resp.json()
            balance_wei = int(data["result"], 16)
            balance_eth = float(balance_wei) / 1e18
            print(balance_eth)
            return balance_eth
        except (ValueError, TypeError) as e:
            raise ValueError(f"Failed to parse balance: {data['result']} - Error: {str(e)}")


@mcp.tool()
async def get_transaction_by_hash(tx_hash: str) -> dict:
    """
    Get a transaction by hash

    Args:
        tx_hash: The hash of the transaction

    Returns:
        The transaction
    """

    async with httpx.AsyncClient() as client:
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getTransactionByHash",
            "params": [tx_hash],
            "id": 1
        }
        headers = {'Content-type': 'application/json'}
        resp = await client.post(rpc_endpoint, json=payload, headers=headers)
        if resp.status_code != 200:
            raise ValueError(f"Error from Ethereum node: {resp.text}")

        print(resp.status_code)
        print(payload)
        print(resp.text)

        data = resp.json()
        return data


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

if __name__ == "__main__":
    # tx = asyncio.run(get_transaction_by_hash("0xd542db3bbb8d0584e46d6d710415ac13d39a81453b44e3f278be8aacec54b8fd"))
    # print(tx)
    app = create_starlette_app(mcp._mcp_server, debug=True)
    uvicorn.run(app, host="0.0.0.0", port=8080)