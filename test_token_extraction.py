#!/usr/bin/env python3
"""
Test token info extraction with real transaction hash
"""

from web3 import Web3, HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware
import json
import os
from dotenv import load_dotenv
from arena_token import Token
import time

# Load environment variables
load_dotenv()

# Configuration
AVAX_RPC = os.getenv('AVAX_RPC')
CONTRACT_ADDRESS = "0x2196E106Af476f57618373ec028924767c758464"

def test_token_extraction(tx_hash):
    """Test token extraction with a real transaction hash"""

    # Setup Web3
    w3 = Web3(HTTPProvider(AVAX_RPC))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    if not w3.is_connected():
        print("❌ Failed to connect to Avalanche RPC")
        return

    # Load contract ABI
    with open('00_TokenManagerERC20/ABI.json', 'r') as f:
        contract_abi = json.load(f)

    contract = w3.eth.contract(
        address=CONTRACT_ADDRESS,
        abi=contract_abi
    )

    print(f"🧪 Testing token extraction...")
    print(f"📦 Transaction hash: {tx_hash}")

    try:
        # Get transaction
        tx = w3.eth.get_transaction(tx_hash)
        print(f"✅ Transaction found")
        print(f"   From: {tx['from']}")
        print(f"   To: {tx.to}")
        print(f"   Block: {tx.blockNumber}")

        # Check if it's to our contract
        if tx.to and tx.to.lower() == CONTRACT_ADDRESS.lower():
            print(f"✅ Transaction is to TokenManager contract")
        else:
            print(f"❌ Transaction is not to TokenManager contract")
            return

        # Decode input data (exactly as in enhanced_detector)
        try:
            decoded = contract.decode_function_input(tx.input)
            function, inputs = decoded

            name = inputs.get('name', '')
            symbol = inputs.get('symbol', '')
            creator_address = inputs.get('tokenCreatorAddress', '')

            print(f"📋 Extracted from input:")
            print(f"   Name: {name}")
            print(f"   Symbol: {symbol}")
            print(f"   Creator: {creator_address}")

        except Exception as e:
            print(f"❌ Failed to decode input: {e}")
            return

        # Get transaction receipt and extract token address and ID
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            print(f"✅ Transaction receipt obtained")

            # Process TokenCreated event
            event = contract.events.TokenCreated().process_receipt(receipt)

            if event:
                print(f"✅ TokenCreated event found")
                token_address = event[0]['args']['params']['tokenContractAddress']
                token_id = event[0]['args']['tokenId']

                print(f"📋 Extracted from event:")
                print(f"   Token Address: {token_address}")
                print(f"   Token ID: {token_id}")

                # Complete token info
                token_info = {
                    'name': name,
                    'symbol': symbol,
                    'creator_address': creator_address,
                    'token_address': token_address,
                    'token_id': str(token_id)
                }

                print(f"\n🎯 COMPLETE TOKEN INFO:")
                for key, value in token_info.items():
                    print(f"   {key}: {value}")

                # Test whitelist functionality with block analysis
                print(f"\n🔍 Testing whitelist functionality...")
                test_whitelist(token_info, w3, tx.blockNumber)

                return token_info

            else:
                print(f"❌ No TokenCreated event found")

        except Exception as e:
            print(f"❌ Failed to process receipt: {e}")
            return

    except Exception as e:
        print(f"❌ Error: {e}")
        return

def test_whitelist(token_info, w3, creation_block):
    """Test whitelist functionality block by block to check propagation timing"""
    try:
        # Create Token instance (same as enhanced_detector)
        token = Token(token_info, w3)

        # Get wallet address from .env
        wallet_address = os.getenv('WALLET_ADDRESS')

        if not wallet_address:
            print("❌ WALLET_ADDRESS not found in .env")
            return

        print(f"   Testing with wallet: {wallet_address}")
        print(f"   Token created in block: {creation_block}")

        # Test whitelist status block by block
        current_block = w3.eth.block_number
        print(f"   Current block: {current_block}")

        # Test from creation block to current block
        blocks_to_test = min(5, current_block - creation_block + 1)

        for i in range(blocks_to_test):
            test_block = creation_block + i
            block_delay = test_block - creation_block

            print(f"\n🔍 Block {test_block} (creation +{block_delay}):")

            # Create fresh token instance for each test
            test_token = Token(token_info, w3)

            if test_token.fetch_whitelist_info(wallet_address):
                wl_status = test_token.get_whitelist_status()

                print(f"   ✅ Whitelisted: {wl_status['is_whitelisted']}")
                if wl_status['is_whitelisted']:
                    print(f"   📅 Start: {wl_status['start_date']}")
                    print(f"   📅 End: {wl_status['end_date']}")
                    print(f"   💰 Max Amount: {wl_status['max_amount']}")

                    # If this is the first time we see whitelisted = True, note it
                    if block_delay > 0:
                        print(f"   🎯 WHITELIST BECAME ACTIVE {block_delay} BLOCKS AFTER CREATION!")
                    break
            else:
                print(f"   ❌ Failed to fetch whitelist info")

            # Small delay between checks
            if i < blocks_to_test - 1:
                time.sleep(0.5)

    except Exception as e:
        print(f"❌ Whitelist test failed: {e}")

if __name__ == "__main__":
    # Test with a real transaction hash
    # Replace with actual createTokenWithWL transaction hash
    test_tx_hash = input("Enter transaction hash to test: ").strip()

    if test_tx_hash:
        test_token_extraction(test_tx_hash)
    else:
        print("❌ No transaction hash provided")