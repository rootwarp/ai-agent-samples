import json

from openai import OpenAI


openai = OpenAI()

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

def get_latest_block_number():
    print('get_latest_block_number')
    return 1234567890


def get_eth_account_balance(account):
    print('get_eth_account_balance', account)
    return 1234567890


function_call_handler = {
    'get_latest_block_number': get_latest_block_number,
    'get_eth_account_balance': get_eth_account_balance,
}


if __name__ == '__main__':
    completion = openai.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{'role': 'user', 'content': "I'd like to know the balance of 0x1234567890123456789012345678901234567890"}],
        tools=tools,
    )

    if completion.choices[0].message.tool_calls is not None:
        for tool_call in completion.choices[0].message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)

            ret = function_call_handler[func_name](**func_args)
            print(f'response of {func_name}: {ret}')
