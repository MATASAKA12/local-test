import os
import time
import threading
import requests
from web3 import Web3
from dotenv import load_dotenv
from web3.providers.websocket import WebsocketProvider
from web3.providers.rpc import HTTPProvider
from telegram import Bot

load_dotenv()   # 👈 this loads your .env file into os.environ

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
ALCHEMY_WSS = os.getenv("ALCHEMY_WSS")
ALCHEMY_HTTP = os.getenv("ALCHEMY_HTTP")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

DEV_WALLET = Web3.to_checksum_address(os.getenv("DEV_WALLET"))
V2_PAIR_ADDRESS = Web3.to_checksum_address(os.getenv("V2_PAIR_ADDRESS"))
V3_MANAGER_ADDRESS = Web3.to_checksum_address(os.getenv("V3_MANAGER_ADDRESS"))

TOKEN_ADDRESS = Web3.to_checksum_address(os.getenv("TOKEN_ADDRESS"))
WALLET_ADDRESS = Web3.to_checksum_address(os.getenv("WALLET_ADDRESS"))
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

SELL_PERCENT = int(os.getenv("SELL_PERCENT", 100))

TOKEN_ID_TO_WATCH = 203
RUG_THRESHOLD_PERCENT = 30.0
TOTAL_SUPPLY_REFRESH_INTERVAL = 60

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

# ──────────────────────────────────────────────
# ABIs
# ──────────────────────────────────────────────
ERC20_ABI = [
    {"constant": True,"inputs": [],"name": "totalSupply","outputs": [{"name": "", "type": "uint256"}],"type": "function"},
    {"anonymous": False,"inputs": [
        {"indexed": True, "name": "from", "type": "address"},
        {"indexed": True, "name": "to", "type": "address"},
        {"indexed": False, "name": "value", "type": "uint256"}],
     "name": "Transfer","type": "event"}
]

ERC721_TRANSFER_ABI = [
    {"anonymous": False,"inputs": [
        {"indexed": True, "name": "from", "type": "address"},
        {"indexed": True, "name": "to", "type": "address"},
        {"indexed": True, "name": "tokenId", "type": "uint256"}],
     "name": "Transfer","type": "event"}
]

# ──────────────────────────────────────────────
# TELEGRAM
# ──────────────────────────────────────────────
bot = Bot(BOT_TOKEN)

def send_telegram(msg: str):
    try:
        bot.send_message(chat_id=CHAT_ID, text=msg)
        print("[ALERT]", msg)
    except Exception as e:
        print("❌ Telegram send failed:", e)

def auto_exit(reason: str):
    send_telegram(f"🛑 AUTO-EXIT SIGNAL\nReason: {reason}\nTake action immediately!")

def fetch_dexscreener(pair_address):
    try:
        url = f"https://api.dexscreener.com/latest/dex/pairs/base/{pair_address}"
        r = requests.get(url, timeout=10)
        data = r.json()
        if "pairs" in data and len(data["pairs"]) > 0:
            p = data["pairs"][0]
            return f"DEXScreener\nPrice: {p['priceUsd']}\nFDV: {p['fdv']}\nLiquidity: {p['liquidity']['usd']}"
    except:
        return "DEXScreener data unavailable"

# ──────────────────────────────────────────────
# V2 LP MONITOR
# ──────────────────────────────────────────────
def monitor_v2_lp():
    w3_ws = Web3(WebsocketProvider(ALCHEMY_WSS))
    w3_http = Web3(HTTPProvider(ALCHEMY_HTTP))

    lp_ws = w3_ws.eth.contract(address=V2_PAIR_ADDRESS, abi=ERC20_ABI)
    lp_http = w3_http.eth.contract(address=V2_PAIR_ADDRESS, abi=ERC20_ABI)

    total_supply = lp_http.functions.totalSupply().call()
    last_refresh = time.time()

    transfer_filter = lp_ws.events.Transfer.create_filter(fromBlock="latest")
    print("[V2] Monitoring LP transfers...")

    while True:
        try:
            if time.time() - last_refresh > TOTAL_SUPPLY_REFRESH_INTERVAL:
                total_supply = lp_http.functions.totalSupply().call()
                last_refresh = time.time()

            for event in transfer_filter.get_new_entries():
                frm = event["args"]["from"]
                to = event["args"]["to"]
                amount = event["args"]["value"]

                # LP Burn / Mint
                if frm == ZERO_ADDRESS:
                    send_telegram("🔥 LP MINT detected")
                if to == ZERO_ADDRESS:
                    send_telegram("🔥 LP BURN detected")

                # Dev wallet move
                if frm == DEV_WALLET:
                    pct = (amount / total_supply) * 100 if total_supply else 0
                    info = fetch_dexscreener(V2_PAIR_ADDRESS)

                    if pct >= RUG_THRESHOLD_PERCENT:
                        send_telegram(f"🚨 DEV LP DUMP {pct:.2f}%\n{info}")
                        auto_exit("Dev dumped LP")

        except Exception as e:
            print("[V2 ERROR]", e)

        time.sleep(2)

# ──────────────────────────────────────────────
# V3 NFT MONITOR
# ──────────────────────────────────────────────
def monitor_v3_nft():
    w3_ws = Web3(WebsocketProvider(ALCHEMY_WSS))
    manager = w3_ws.eth.contract(address=V3_MANAGER_ADDRESS, abi=ERC721_TRANSFER_ABI)
    transfer_filter = manager.events.Transfer.create_filter(fromBlock="latest")

    print("[V3] Monitoring NFT transfers...")

    while True:
        try:
            for event in transfer_filter.get_new_entries():
                if event["args"]["from"] == DEV_WALLET:
                    send_telegram("🚨 DEV moved V3 LP NFT")
                    auto_exit("V3 LP NFT moved")
        except Exception as e:
            print("[V3 ERROR]", e)

        time.sleep(2)

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
if __name__ == "__main__":
    send_telegram("🧪 Bot online & monitoring started")
    threading.Thread(target=monitor_v2_lp, daemon=True).start()
    threading.Thread(target=monitor_v3_nft, daemon=True).start()

    print("✅ LP Rug Bot running...")
    while True:
        time.sleep(10)
