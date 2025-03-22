from flask import Blueprint, request, jsonify
from web3 import Web3
from eth_account.messages import encode_defunct
from eth_account import Account
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import os

# 加载 .env 文件
load_dotenv()





payments_bp = Blueprint('payments', __name__)

# Initialize Web3
# INFURA_URL = os.getenv('INFURA_URL', 'https://sepolia.infura.io/v3/c193f02a083648b4b66c7eeaa13fa988')
INFURA_URL = os.getenv('INFURA_URL', 'https://sepolia.base.org')
web3 = Web3(Web3.HTTPProvider(INFURA_URL))


# Relayer wallet
NNZDD_CONTRACT_ADDR = os.getenv("NNZDD_CONTRACT_ADDR")

# Relayer wallet
RELAYER_PRIVATE_KEY = os.getenv("RELAYER_PRIVATE_KEY")
relayer_account = Account.from_key(RELAYER_PRIVATE_KEY) if RELAYER_PRIVATE_KEY else None

# Chain ID
CHAIN_ID = int(os.getenv('CHAIN_ID', 11155111)) # Default to Ethereum mainnet

# Relayer contract
RELAYER_CONTRACT_ADDRESS = os.getenv('RELAYER_CONTRACT_ADDRESS')
# RELAYER_CONTRACT_ADDRESS = "0x925b21Db4357b1fc3Face4FD34F56916E17320bA"
# Load ABIs
try:
    with open('app/contracts/ERC20WithPermit.json', 'r') as f:
        contract_json = json.load(f)
        # ERC20_PERMIT_ABI = contract_json['erc20PermitAbi']
        ERC20_PERMIT_ABI = contract_json['abi']
        PAYMENT_RELAYER_ABI = contract_json['paymentRelayerAbi']
except Exception as e:
    print(f"Error loading ABI files: {str(e)}")
    ERC20_PERMIT_ABI = []
    PAYMENT_RELAYER_ABI = []

# Load supported tokens configuration
SUPPORTED_TOKENS = {
    # "0x0000000000000000000000000000000000000000": {
    #     "symbol": "ETH",
    #     "name": "Ethereum",
    #     "supports_permit": False,
    # },
    NNZDD_CONTRACT_ADDR : {
        "symbol": "NNZDD",
        "name": " Stablecoin",
        "supports_permit": True,
    },
}
# try:
#     tokens_json = os.getenv('SUPPORTED_TOKENS', '{}')
#     SUPPORTED_TOKENS = json.loads(tokens_json)
# except Exception as e:
#     print(f"Error loading supported tokens: {str(e)}")

@payments_bp.route('/health', methods=['GET'])
def health_check():
    """Endpoint to check if the relayer is online and connected to Ethereum"""
    if web3.is_connected():
        return jsonify({
            'status': 'online',
            'ethereum_connected': True,
            'relayer_address': relayer_account.address if relayer_account else None,
            'relayer_contract': RELAYER_CONTRACT_ADDRESS,
            'current_block': web3.eth.block_number,
            'chain_id': web3.eth.chain_id
        })
    return jsonify({
        'status': 'online',
        'ethereum_connected': False
    }), 500

@payments_bp.route('/supported-tokens', methods=['GET'])
def supported_tokens():
    """Return the list of supported token addresses and their metadata"""
    print(SUPPORTED_TOKENS)
    return jsonify(SUPPORTED_TOKENS)

@payments_bp.route('/token-info/<address>', methods=['GET'])
def token_info(address):
    """Get information about a specific token"""
    try:
        # Check if we have the token in our supported list
        if address.lower() in SUPPORTED_TOKENS:
            return jsonify(SUPPORTED_TOKENS[address.lower()])
        
        # If not in our list, try to fetch from blockchain
        token_address = Web3.to_checksum_address(address)
        token_contract = web3.eth.contract(address=token_address, abi=ERC20_PERMIT_ABI)
        
        # Basic info
        try:
            name = token_contract.functions.name().call()
            symbol = token_contract.functions.symbol().call()
            decimals = token_contract.functions.decimals().call()
            
            # Check if permit is supported
            supports_permit = False
            try:
                # Just check if the function exists by calling the domain separator
                domain_separator = token_contract.functions.DOMAIN_SEPARATOR().call()
                supports_permit = True
            except:
                supports_permit = False
            
            return jsonify({
                'name': name,
                'symbol': symbol,
                'decimals': decimals,
                'address': address,
                'supports_permit': supports_permit
            })
        except Exception as e:
            return jsonify({
                'error': f"Could not retrieve token info: {str(e)}",
                'supports_permit': False
            }), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@payments_bp.route('/get-nonce/<token_address>/<wallet_address>', methods=['GET'])
def get_nonce(token_address, wallet_address):
    """Get the current nonce for a wallet with a specific token's permit function"""
    try:
        token_address = Web3.to_checksum_address(token_address)
        wallet_address = Web3.to_checksum_address(wallet_address)
        
        # Connect to token contract
        token_contract = web3.eth.contract(address=token_address, abi=ERC20_PERMIT_ABI)
        
        # Get nonce from the token contract
        try:
            nonce = token_contract.functions.nonces(wallet_address).call()
            return jsonify({'nonce': nonce})
        except Exception as e:
            return jsonify({'error': f"Token does not support EIP-2612 permit: {str(e)}"}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@payments_bp.route('/submit-transaction', methods=['POST'])
def submit_transaction():
    """
    Submit a gasless transaction using the relayer contract and EIP-2612 permit
    
    Expected payload:
    {
        "token_address": "0x...",
        "sender": "0x...",
        "recipient": "0x...",
        "amount": "1000000000000000000", // Wei amount as string
        "deadline": 1729142399, // Unix timestamp
        "collect_fee": true, // Whether to collect the relayer fee
        "signature": {
            "v": 27,
            "r": "0x...",
            "s": "0x..."
        }
    }
    """
    try:
        data = request.get_json()
        
        # Validate request data
        required_fields = ['token_address', 'sender', 'recipient', 'amount', 'deadline', 'signature']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Get signature components
        v, r, s = data['signature'].get('v'), data['signature'].get('r'), data['signature'].get('s')
        
        if not all([v, r, s]):
            return jsonify({'error': 'Invalid signature components'}), 400
        
        # Connect to the token contract and relayer contract
        token_address = Web3.to_checksum_address(data['token_address'])
        sender = Web3.to_checksum_address(data['sender'])
        recipient = Web3.to_checksum_address(data['recipient'])
        
        # Convert amount to int if it's a string
        amount = int(data['amount']) if isinstance(data['amount'], str) else data['amount']
        deadline = int(data['deadline'])
        collect_fee = data.get('collect_fee', True)
        
        # Connect to the relayer contract
        if not RELAYER_CONTRACT_ADDRESS:
            return jsonify({'error': 'Relayer contract address not configured'}), 500
        
        relayer_contract = web3.eth.contract(
            address=Web3.to_checksum_address(RELAYER_CONTRACT_ADDRESS),
            abi=PAYMENT_RELAYER_ABI
        )
        
        # Check that relayer is an operator
        is_operator = relayer_contract.functions.operators(relayer_account.address).call()
        if not is_operator:
            return jsonify({'error': 'Relayer wallet is not an authorized operator'}), 500
        
        # Build and send the transaction to the relayer contract
        try:
            relay_tx = relayer_contract.functions.relayPayment(
                token_address,
                sender,
                recipient,
                amount,
                deadline,
                v, r, s,
                collect_fee
            ).build_transaction({
                'from': relayer_account.address,
                'nonce': web3.eth.get_transaction_count(relayer_account.address),
                'gas': 300000,  # Higher gas limit for the relayer function
                'gasPrice': web3.eth.gas_price
            })
            
            # Sign and send the transaction
            signed_tx = web3.eth.account.sign_transaction(relay_tx, RELAYER_PRIVATE_KEY)
            # tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

            return jsonify({
                'status': 'success',
                'tx_hash': tx_hash.hex(),
                'message': 'Transaction submitted to blockchain'
            })
            
        except Exception as e:
            print(f"Transaction error: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    except Exception as e:
        print(f"Server error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@payments_bp.route('/verify-signature', methods=['POST'])
def verify_signature():
    """Endpoint to verify a permit signature before submitting the transaction"""
    try:
        data = request.get_json()
        
        # Validate request
        required_fields = ['token_address', 'sender', 'recipient', 'amount', 'deadline', 'signature']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Get signature components
        v, r, s = data['signature'].get('v'), data['signature'].get('r'), data['signature'].get('s')
        
        if not all([v, r, s]):
            return jsonify({'error': 'Invalid signature components'}), 400
        
        # Connect to the token contract
        token_address = Web3.to_checksum_address(data['token_address'])
        token_contract = web3.eth.contract(address=token_address, abi=ERC20_PERMIT_ABI)
        
        # Get token name for the domain
        try:
            token_name = token_contract.functions.name().call()
            
            # Build the EIP-712 domain and message
            from app.utils.signature import recover_signer
            
            # Recover the signer address
            recovered_address = recover_signer(
                web3,
                token_name,
                token_address,
                CHAIN_ID,
                data['sender'],
                RELAYER_CONTRACT_ADDRESS, # The spender should be the relayer contract
                int(data['amount']) if isinstance(data['amount'], str) else data['amount'],
                0,  # We don't know the actual nonce used in the signature
                int(data['deadline']),
                {'v': v, 'r': r, 's': s}
            )
            
            # Check if the recovered address matches the sender
            is_valid = recovered_address.lower() == data['sender'].lower()
            
            return jsonify({
                'is_valid': is_valid,
                'recovered_address': recovered_address
            })
        
        except Exception as e:
            return jsonify({
                'error': f"Could not verify signature: {str(e)}",
                'is_valid': False
            }), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 