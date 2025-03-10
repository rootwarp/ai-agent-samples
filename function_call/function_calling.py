import json

import httpx
from openai import OpenAI


rpc_endpoint = "https://ethereum.publicnode.com"


def get_latest_block_number():
    with httpx.Client() as client:
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_blockNumber",
            "params": [],
            "id": 1
        }
        headers = {'Content-type': 'application/json'}
        resp = client.post(rpc_endpoint, json=payload, headers=headers)
        if resp.status_code != 200:
            raise ValueError(f"Error from Ethereum node: {resp.text}")

        data = resp.json()
        return int(data["result"], 16)


def get_eth_account_balance(account):
    with httpx.Client() as client:
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getBalance",
            "params": [account, "latest"],
            "id": 1
        }
        headers = {'Content-type': 'application/json'}
        resp = client.post(rpc_endpoint, json=payload, headers=headers)
        if resp.status_code != 200:
            raise ValueError(f"Error from Ethereum node: {resp.text}")

        try:
            data = resp.json()
            balance_wei = int(data["result"], 16)
            balance_eth = float(balance_wei) / 1e18

            return balance_eth
        except (ValueError, TypeError) as e:
            raise ValueError(f"Failed to parse balance: {data['result']} - Error: {str(e)}")


tools = [
    {
        'type': 'function',
        'function': {
            'name': 'get_latest_block_number',
            'description': 'Get the latest block number on the Ethereum blockchain.',
            'parameters': {
                'type': 'object',
                'properties': {},
                'required': [],
                'additionalProperties': False,
            },
            'strict': True,
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_eth_account_balance',
            'description': 'Get the balance of an Ethereum account.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'account': {
                        'type': 'string',
                        'description': 'The Ethereum account to get the balance of, which starts with 0x and is 42 characters long.',
                    },
                },
                'required': ['account'],
                'additionalProperties': False,
            },
            'strict': True,
        },
    },
]

function_call_handler = {
    'get_latest_block_number': get_latest_block_number,
    'get_eth_account_balance': get_eth_account_balance,
}


if __name__ == '__main__':
    openai = OpenAI()
    completion = openai.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {'role': 'user', 'content': "I'd like to know the balance of 0x8C8D7C46219D9205f056f28fee5950aD564d7465"},
        ],
        tools=tools,
    )

    if completion.choices[0].message.tool_calls is not None:
        print(f"tool_calls: {completion.choices[0].message.tool_calls}")

        for tool_call in completion.choices[0].message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)

            ret = function_call_handler[func_name](**func_args)
            print(f'response of {func_name}: {ret}')
