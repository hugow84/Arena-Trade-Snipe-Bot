#!/usr/bin/env python3
"""
Token class for detected tokens
Handles token analysis and whitelist information
"""
from eth_utils import to_checksum_address
from web3 import Web3, HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware
import json
import os
from datetime import datetime
import numpy as np
# Configuration
AVAX_RPC = os.getenv('AVAX_RPC', 'https://avax-mainnet.g.alchemy.com/v2/QCC_EnyFveVA8WFP9L0Y7_kX8jXpMXpo')

def unix_to_readable(timestamp):
    """Convert Unix timestamp to readable date format"""
    if not timestamp:
        return None
    try:
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, OSError):
        return None

class Token:
    def __init__(self, token_info, w3_instance=None):
        """
        Initialize Token with basic info from detector
        token_info: dict with name, symbol, creator_address, token_address, token_id
        """
        # Basic token info
        self.name = token_info.get('name', '')
        self.symbol = token_info.get('symbol', '')
        self.creator_address = token_info.get('creator_address', '')
        self.token_address = to_checksum_address(token_info.get('token_address', ''))
        self.token_id = token_info.get('token_id', '')
        self.token_supply = 10000000000000000000000000000

        # Whitelist info (will be populated when retrieved)
        self.is_whitelisted = None
        self.wl_end_timestamp = None
        self.wl_max_amount = None
        self.wl_start_timestamp = None

        # Web3 setup
        if w3_instance:
            self.w3 = w3_instance
        else:
            self.w3 = Web3(HTTPProvider(AVAX_RPC))
            self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        # Load token contract ABI
        with open('01_TokenTemplate/ABI.json', 'r') as f:
            self.token_abi = json.load(f)

        # Load TokenManager contract ABI for buying
        with open('00_TokenManagerERC20/ABI.json', 'r') as f:
            self.manager_abi = json.load(f)

        # Create contract instances
        if self.token_address:
            self.contract = self.w3.eth.contract(
                address=self.token_address,
                abi=self.token_abi
            )
        else:
            self.contract = None

        # TokenManager contract for buying
        manager_address = os.getenv('TOKEN_MANAGER_ADDRESS', '0x2196E106Af476f57618373ec028924767c758464')
        self.manager_contract = self.w3.eth.contract(
            address=manager_address,
            abi=self.manager_abi
        )

    def get_basic_info(self):
        """Get basic token information"""
        return {
            'name': self.name,
            'symbol': self.symbol,
            'creator': self.creator_address,
            'address': self.token_address,
            'token_id': self.token_id
        }

    def fetch_whitelist_info(self, user_address):
        """
        Fetch and store whitelist information for a specific address
        Updates class variables with whitelist data
        """
        if not self.contract:
            return False

        try:
            result = self.contract.functions.getWhiteListInformation(user_address).call()

            # Store whitelist info in class variables
            self.is_whitelisted = result[0]      # Bool - WL status
            self.wl_end_timestamp = result[1]    # Unix timestamp - WL end
            self.wl_max_amount = result[2]       # Token amount - max supply
            self.wl_start_timestamp = result[3]  # Unix timestamp - WL start

            return True
        except Exception as e:
            print(f"Error fetching whitelist info: {e}")
            return False

    def get_whitelist_status(self):
        """Get current whitelist status"""
        return {
            'is_whitelisted': self.is_whitelisted,
            'start_timestamp': self.wl_start_timestamp,
            'end_timestamp': self.wl_end_timestamp,
            'max_amount': self.wl_max_amount,
            'start_date': unix_to_readable(self.wl_start_timestamp),
            'end_date': unix_to_readable(self.wl_end_timestamp)
        }

    def get_price(self, amount_tokens):
        """
        Get price in ARENA (Wei) for buying tokens including fees
        amount_tokens: Amount of tokens (unit-adjusted, 1 = 1 token)
        Returns: Price in ARENA Wei
        """
        try:
            return self.manager_contract.functions.calculateCostWithFees(
                amount_tokens,
                int(self.token_id)
            ).call()
        except Exception as e:
            print(f"❌ Price calculation failed: {e}")
            return None

    def buy_tokens(self, amount, private_key, max_arena_spend=None, gas_limit=500000, gas_price_gwei=10):
        """
        Buy tokens using buyAndCreateLpIfPossible
        amount: Amount of tokens to buy (uint256)
        private_key: Private key for transaction signing
        max_arena_spend: Maximum ARENA tokens to spend (if None, uses a safe large value)
        gas_limit: Gas limit for transaction
        gas_price_gwei: Gas price in Gwei
        """
        try:
            from eth_account import Account

            # Get wallet address from private key
            account = Account.from_key(private_key)
            wallet_address = account.address

            # If no max_arena_spend provided, use a large safe value (1000 ARENA)
            if max_arena_spend is None:
                max_arena_spend = self.w3.to_wei(1000, 'ether')  # 1000 ARENA tokens
            else:
                # Convert to Wei if it's in ARENA units
                max_arena_spend = self.w3.to_wei(max_arena_spend, 'ether')

            # Convert gas price to Wei
            gas_price_wei = self.w3.to_wei(gas_price_gwei, 'gwei')

            # Get current nonce
            nonce = self.w3.eth.get_transaction_count(wallet_address)

            # Build transaction for buyAndCreateLpIfPossible
            transaction = self.manager_contract.functions.buyAndCreateLpIfPossible(
                amount,                 # amount of tokens to buy
                int(self.token_id),     # token ID
                max_arena_spend         # max ARENA to spend
            ).build_transaction({
                'from': wallet_address,
                'gas': gas_limit,
                'gasPrice': gas_price_wei,
                'nonce': nonce,
                'chainId': 43114  # Avalanche mainnet
            })

            # Sign transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, private_key)

            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)

            print(f"✅ Buy transaction sent: {tx_hash.hex()}")
            print(f"   Amount: {amount}")
            print(f"   Token ID: {self.token_id}")
            print(f"   Max ARENA spend: {self.w3.from_wei(max_arena_spend, 'ether')} ARENA")

            return tx_hash.hex()

        except Exception as e:
            print(f"❌ Buy transaction failed: {e}")
            return None

    def smart_buy(self, private_key, max_arena_threshold, target_amount=None):
        """
        Smart buy function that respects whitelist limits and ARENA threshold
        private_key: Wallet private key
        max_arena_threshold: Maximum ARENA to spend
        target_amount: Desired token amount (uses whitelist max if None)
        """
        try:
            # Use whitelist max amount if no target specified
            if target_amount is None:
                if self.wl_max_amount:
                    # Convert from Wei to token units for price calculation
                    target_amount = int(self.wl_max_amount // (10**18))
                else:
                    print("❌ No target amount and no whitelist max amount available")
                    return None

            print(f"🎯 Smart buy starting...")
            print(f"   Target amount: {target_amount} tokens")
            print(f"   ARENA threshold: {max_arena_threshold} ARENA")

            # Find optimal amount within threshold
            optimal_amount = self._find_optimal_amount(target_amount, max_arena_threshold)

            if optimal_amount is None:
                print("❌ No viable amount found within threshold")
                return None

            # Convert to Wei for actual purchase
            amount_wei = optimal_amount * (10**18)

            # Get final price estimate and double it for safety
            estimated_cost = self.get_price(optimal_amount)
            max_spend = estimated_cost * 3  # Double for flexibility

            print(f"💸 Final purchase parameters:")
            print(f"   Amount: {optimal_amount} tokens ({amount_wei} Wei)")
            print(f"   Estimated cost: {self.w3.from_wei(estimated_cost, 'ether'):.6f} ARENA")
            print(f"   Max spend (2x): {self.w3.from_wei(max_spend, 'ether'):.6f} ARENA")

            # Execute purchase with retry
            for attempt in range(3):  # Try 3 times
                tx_hash = self.buy_tokens(
                    amount=amount_wei,
                    private_key=private_key,
                    max_arena_spend=self.w3.from_wei(max_spend, 'ether'),
                    gas_limit=500000,
                    gas_price_gwei=50
                )

                if tx_hash:
                    # Check if transaction succeeded
                    try:
                        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
                        if receipt.status == 1:
                            return tx_hash
                        else:
                            print(f"❌ Transaction failed (status: 0)")
                    except Exception as e:
                        print(f"❌ Transaction check failed: {e}")

                # If failed, increase max spend and retry
                if attempt < 2:
                    max_spend = np.max(max_spend * 2, self.w3.to_wei(8000, 'ether'))
                    print(f"🔄 Retry {attempt + 2}/3 with higher max spend: {self.w3.from_wei(max_spend, 'ether'):.6f} ARENA")

            print(f"❌ All 3 attempts failed")
            return None

        except Exception as e:
            print(f"❌ Smart buy failed: {e}")
            return None

    def _find_optimal_amount(self, target_amount, max_arena_threshold):
        """
        Recursively find optimal token amount within ARENA threshold
        """
        current_amount = target_amount
        threshold_wei = self.w3.to_wei(max_arena_threshold, 'ether')

        while current_amount > 0:
            estimated_cost = self.get_price(current_amount)

            if estimated_cost and estimated_cost <= threshold_wei:
                print(f"✅ Found optimal amount: {current_amount} tokens")
                print(f"   Cost: {self.w3.from_wei(estimated_cost, 'ether'):.6f} ARENA")
                return current_amount

            # Reduce by 10% and try again
            current_amount = int(current_amount * 0.7)

            if current_amount < 100:  # Minimum viable amount
                break

        return None

    def print_info(self):
        """Print formatted token information"""
        print(f"\n📋 Token: {self.name} ({self.symbol})")
        print(f"   Address: {self.token_address}")
        print(f"   Token ID: {self.token_id}")
        print(f"   Creator: {self.creator_address}")

        if self.is_whitelisted is not None:
            print(f"\n🎫 Whitelist Status:")
            print(f"   Whitelisted: {self.is_whitelisted}")
            print(f"   Start: {unix_to_readable(self.wl_start_timestamp)} ({self.wl_start_timestamp})")
            print(f"   End: {unix_to_readable(self.wl_end_timestamp)} ({self.wl_end_timestamp})")
            print(f"   Max Amount: {self.wl_max_amount}")
        else:
            print(f"   ⚠️ Whitelist info not fetched yet")