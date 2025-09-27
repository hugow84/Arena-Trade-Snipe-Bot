#!/usr/bin/env python3
"""
Enhanced Token Detector - Detects and extracts token info
"""

from web3 import Web3, HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware
import json
import time
import os
import warnings
from datetime import datetime
from dotenv import load_dotenv
from arena_token import Token

# Suppress Web3 event processing warnings
warnings.filterwarnings("ignore", "The log with transaction hash")

# Load environment variables
load_dotenv()

# Configuration
AVAX_RPC = os.getenv('AVAX_RPC')
CONTRACT_ADDRESS = "0x2196E106Af476f57618373ec028924767c758464"
POLL_INTERVAL = 0.3
WALLET_ADDRESS = os.getenv('WALLET_ADDRESS')
WALLET_PRIVATE_KEY = os.getenv('WALLET_PRIVATE_KEY')
MAX_ARENA_SPEND = 10000 
# Method IDs
METHOD_IDS = {
    #"createToken": "0x1a5a3831",
    "createTokenWithWL": "0x4ac42e71"
}

class EnhancedDetector:
    def __init__(self):
        # Setup Web3
        self.w3 = Web3(HTTPProvider(AVAX_RPC))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to Avalanche RPC")

        # Load contract ABI
        with open('00_TokenManagerERC20/ABI.json', 'r') as f:
            self.contract_abi = json.load(f)

        self.contract = self.w3.eth.contract(
            address=CONTRACT_ADDRESS,
            abi=self.contract_abi
        )

        print(f"✅ Connected to Avalanche - Block: {self.w3.eth.block_number}")
        self.detected_count = 0
        self.pending_buys = []  # List of scheduled purchases

    def extract_token_info(self, tx):
        """Extract token info from transaction"""
        try:
            # Decode input data
            decoded = self.contract.decode_function_input(tx.input)
            function, inputs = decoded

            
            name = inputs.get('name', '')
            symbol = inputs.get('symbol', '')
            creator_address = inputs.get('tokenCreatorAddress', '')

            # Get token contract address from logs
            receipt = self.w3.eth.get_transaction_receipt(tx.hash)
            event = self.contract.events.TokenCreated().process_receipt(receipt)
            token_address = event[0]['args']['params']['tokenContractAddress']
            token_id = event[0]['args']['tokenId']

            return {
                'name': name,
                'symbol': symbol,
                'creator_address': creator_address,
                'token_address': token_address,
                'token_id': token_id
            }

        except Exception as e:
            return None

    def check_transaction(self, tx, block_number: int) -> bool:
        """Check if transaction is a token creation"""
        try:
            if not tx.to or tx.to.lower() != CONTRACT_ADDRESS.lower():
                return False

            tx_input = tx.input.hex()

            # Check method signature
            matched_method = None
            for method_name, method_id in METHOD_IDS.items():
                if tx_input.startswith(method_id[2:]):
                    matched_method = method_name
                    break

            if matched_method:
                self.detected_count += 1

                # Extract token info
                token_info = self.extract_token_info(tx)

                if token_info:
                    # Create Token object
                    token = Token(token_info, self.w3)

                    print(f"\n🎯 TOKEN #{self.detected_count} - {matched_method}")

                    # Fetch whitelist info first for createTokenWithWL
                    if matched_method == "createTokenWithWL":
                        if WALLET_ADDRESS:
                            print(f"🔍 Checking whitelist status for wallet...")
                            token.fetch_whitelist_info(WALLET_ADDRESS)

                            # Auto-buy if whitelisted and we have credentials
                            if token.is_whitelisted and WALLET_PRIVATE_KEY:
                                current_time = int(time.time())

                                if current_time >= token.wl_start_timestamp:
                                    # Whitelist already started - buy now
                                    print(f"🚀 WHITELISTED! Attempting auto-buy...")
                                    tx_hash = token.smart_buy(
                                        private_key=WALLET_PRIVATE_KEY,
                                        max_arena_threshold=MAX_ARENA_SPEND
                                    )
                                    if tx_hash:
                                        print(f"🎉 AUTO-BUY SUCCESS! TX: {tx_hash}")
                                    else:
                                        print(f"❌ Auto-buy failed")
                                else:
                                    # Whitelist starts in future - schedule it
                                    self.pending_buys.append({
                                        'token': token,
                                        'private_key': WALLET_PRIVATE_KEY,
                                        'max_spend': MAX_ARENA_SPEND,
                                        'start_timestamp': token.wl_start_timestamp
                                    })
                                    start_time_str = datetime.fromtimestamp(token.wl_start_timestamp).strftime('%Y-%m-%d %H:%M:%S')
                                    print(f"📅 Scheduled for {start_time_str}")
                            elif token.is_whitelisted:
                                print(f"✅ Whitelisted but missing WALLET_PRIVATE_KEY")
                            else:
                                print(f"❌ Not whitelisted")
                        else:
                            print(f"   ⚠️ WALLET_ADDRESS not found in .env")

                
                else:
                    print(f"\n🎯 TOKEN #{self.detected_count} - {matched_method} (decode failed)")
                    print(f"   Block: {block_number}")

                return True

        except Exception as e:
            print(f"❌ Error processing tx: {e}")

        return False

    def check_pending_buys(self):
        """Check and execute any pending buys that are ready"""
        current_time = int(time.time())
        executed = []

        for i, pending in enumerate(self.pending_buys):
            if current_time >= pending['start_timestamp']:
                tx_hash = pending['token'].smart_buy(
                    private_key=pending['private_key'],
                    max_arena_threshold=pending['max_spend']
                )
                if tx_hash:
                    print(f"🎉 SCHEDULED BUY SUCCESS! TX: {tx_hash}")
                executed.append(i)

        # Remove executed buys
        for i in reversed(executed):
            self.pending_buys.pop(i)

    def scan_blocks(self):
        """Main scanning loop"""
        print(f"🔍 Enhanced token detector started")
        last_block = self.w3.eth.block_number

        try:
            while True:
                current_block = self.w3.eth.block_number

                while last_block <= current_block:
                    try:
                        block = self.w3.eth.get_block(last_block, full_transactions=True)
                        for tx in block.transactions:
                            self.check_transaction(tx, last_block)
                    except Exception as e:
                        print(f"❌ Error fetching block {last_block}: {e}")
                    last_block += 1

                # Check pending buys every few blocks
                if last_block % 2 == 0 and self.pending_buys:
                    self.check_pending_buys()

                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print(f"\n🛑 Detection stopped - Total: {self.detected_count}")

def main():
    try:
        detector = EnhancedDetector()
        detector.scan_blocks()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"💥 Error: {e}")

if __name__ == "__main__":
    main()