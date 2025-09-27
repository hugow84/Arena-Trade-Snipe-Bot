# Arena Snipe

A token sniper for Avalanche blockchain targeting specific token factory contracts.

## Overview

Arena Snipe is designed to detect and analyze new token creations on the Avalanche blockchain, specifically monitoring the token factory contract at `0x2196E106Af476f57618373ec028924767c758464`.

## Features

- **Real-time Detection**: Monitors blockchain for `createToken` and `createTokenWithWL` transactions
- **Token Analysis**: Extracts token information including name, symbol, creator address, and token address
- **Whitelist Support**: Analyzes token whitelist parameters and timing
- **Simple Architecture**: Focused approach without unnecessary complexity

## Components

### Core Files
- `enhanced_detector.py` - Main blockchain listener and transaction detection engine
- `arena_token.py` - Token class for post-detection analysis and whitelist information
- `utils.py` - Utility functions

### Contract Information
- `00_TokenManagerERC20/` - Token manager contract ABI and information
- `01_TokenTemplate/` - Individual token contract details and functions

### Testing
- `test_*.py` - Testing files for feature development

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Configuration**
   Create a `.env` file with:
   ```
   AVAX_RPC=your_avalanche_rpc_endpoint
   WALLET_ADDRESS=your_wallet_address
   WALLET_PRIVATE_KEY=your_private_key
   ```

3. **Run the Detector**
   ```bash
   python enhanced_detector.py
   ```

## Development Approach

This project follows a **step-by-step development methodology**:

1. **Never build everything at once**
2. **Always create test files first** - test new functionality in isolation
3. **Never alter existing working code** during testing phase
4. **Only integrate when feature is working**
5. **Test incrementally** - one feature at a time

### Workflow Pattern
```
1. Create test_[feature].py
2. Develop and test feature in isolation
3. Verify functionality works
4. Create production file
5. Integrate with existing core only when stable
```

## Target Contract

- **Address**: `0x2196E106Af476f57618373ec028924767c758464`
- **Network**: Avalanche C-Chain
- **Functions Monitored**:
  - `createToken` - Basic token creation
  - `createTokenWithWL` - Token creation with whitelist

## Key Token Functions

From the token template contracts:
- `getWhiteListInformation(address)` - Check whitelist status
- `whitelistedAddresses(address)` - Direct whitelist check
- `whitelist()` - Whitelist parameters (timing, limits)
- `whitelistStartTimestamp()` / `whiteListOffTimestamp()` - Timing information

## Configuration

- **Poll Interval**: 0.3 seconds
- **Max Arena Spend**: 10,000 tokens
- **Target Methods**: `createTokenWithWL` (0x4ac42e71)

## Security Notes

- Keep private keys secure and never commit them to the repository
- Use environment variables for all sensitive configuration
- Test thoroughly before running on mainnet

## Contributing

Follow the established development methodology:
1. Create test files for new features
2. Test in isolation
3. Only integrate when stable
4. Maintain simplicity and focus

## License

This project is for educational and research purposes.