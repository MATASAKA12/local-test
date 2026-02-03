import time
import os
from web3 import Web3
from web3.providers.rpc import HTTPProvider
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────
# ENV
# ──────────────────────────────────────────────
ALCHEMY_HTTP = os.getenv("ALCHEMY_HTTP")
TOKEN_ADDRESS = Web3.to_checksum_address(os.getenv("TOKEN_ADDRESS"))
WALLET_ADDRESS = Web3.to_checksum_address(os.getenv("WALLET_ADDRESS"))
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

UNISWAP_ROUTER = Web3.to_checksum_address("0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24")

# ──────────────────────────────────────────────
# ERC20 ABI (approve only)
# ──────────────────────────────────────────────
ERC20_APPROVE_ABI = [
    {
        "name": "approve",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "outputs": [{"name": "", "type": "bool"}]
    }
]

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    w3 = Web3(HTTPProvider(ALCHEMY_HTTP))
    if not w3.is_connected():
        raise RuntimeError("❌ HTTP connection failed")

    token = w3.eth.contract(address=TOKEN_ADDRESS, abi=ERC20_APPROVE_ABI)

    # Max uint256 = infinite approval
    MAX_UINT = 2**256 - 1

    nonce = w3.eth.get_transaction_count(WALLET_ADDRESS)
    gas_price = w3.eth.gas_price

    tx = token.functions.approve(
        UNISWAP_ROUTER,
        MAX_UINT
    ).build_transaction({
        "from": WALLET_ADDRESS,
        "gas": 100000,
        "gasPrice": gas_price,
        "nonce": nonce,
    })

    signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)

    print("✅ Approval sent!")
    print("Tx hash:", tx_hash.hex())
    print("Wait 30–60 seconds before running your bot.")

if __name__ == "__main__":
    main()
