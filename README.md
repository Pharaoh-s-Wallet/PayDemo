# TahiPay - Gasless ERC20 Payment System

TahiPay is a subsidized payment system that allows users to send ERC20 tokens without paying for gas fees. The system uses the EIP-2612 permit standard along with a smart contract relayer to perform the transactions on behalf of the user.

## How It Works

1. **User Signs a Permit Message**: Instead of sending an `approve` transaction, the user signs a permit message using their wallet (e.g., MetaMask). This signature authorizes the relayer smart contract to spend a specific amount of tokens.

2. **Signature is Sent to Relayer Backend**: The signed message is sent to our backend, which then interacts with the blockchain.

3. **Backend Calls Relayer Contract**: Our backend calls the relayer smart contract, which:
   - First calls the `permit()` function on the token contract to set the allowance.
   - Then transfers the tokens from the user to the recipient.

4. **Gas Fees are Covered**: The relayer pays for the gas fees, making the transaction gasless for the user.

## Technical Architecture

### Smart Contracts

- **PaymentRelayer Contract**: A dedicated contract that handles the permit verification and token transfer in a single transaction.

### Backend (Flask)

- **Flask API**: Handles incoming signature requests and relays transactions to the blockchain.
- **Web3.py**: Interacts with Ethereum blockchain and our relayer contract.

### Frontend

- **Web Interface**: Allows users to connect their wallet and sign permit messages.
- **Web3.js/ethers.js**: Handles wallet connection and signing.

## Supported Tokens

Only ERC20 tokens that implement the EIP-2612 permit standard can be used with this system. Common examples include:
- NNZDD (deploy by team)


## Prerequisites

- Python 3.7+
- Flask with compatible Werkzeug
- Web3.py
- MetaMask or compatible wallet
- Infura account or other Ethereum node provider
- Deployed PaymentRelayer contract

## Installation

1. Clone the repository:
```
git clone git@github.com:Pharaoh-s-Wallet/PaymentRelayer.git
cd PaymentRelayer
```

2. Install required packages:
```
pip install -r requirements.txt
```

3. Create a `.env` file based on `.env.example` and fill in your configuration:
```
cp .env.example .env
# Edit .env with your values
```

4. Run the application:
```
python run.py
```

## Smart Contract Deployment

1. Deploy the PaymentRelayer contract to your preferred network.
2. Update the `.env` file with the contract address.
3. Add your relayer wallet as an operator in the contract.

## API Endpoints

### `GET /api/health`
Check if the relayer is online and connected to the blockchain.

### `GET /api/supported-tokens`
Get a list of supported tokens and their details.

### `GET /api/token-info/<address>`
Get information about a specific token.

### `GET /api/get-nonce/<token_address>/<wallet_address>`
Get the current nonce for a wallet with a specific token's permit function.

### `POST /api/submit-transaction`

Submit a signed permit and execute a token transfer.

**Request Body**:
```json
{
  "token_address": "0x...",
  "sender": "0x...",
  "recipient": "0x...",
  "amount": "1000000000000000000",
  "deadline": 1729142399,
  "collect_fee": true,
  "signature": {
    "v": 27,
    "r": "0x...",
    "s": "0x..."
  }
}
```


## License

MIT
 