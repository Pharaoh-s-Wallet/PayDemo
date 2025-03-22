from web3 import Web3
from eth_account.messages import encode_defunct
from eth_account import Account
import json
import time

def get_domain_data(token_name, token_address, chain_id):
    """
    Generate domain data for EIP-712 typed data
    """
    return {
        'name': token_name,
        'version': '1',
        'chainId': chain_id,
        'verifyingContract': token_address
    }

def get_permit_data(owner, spender, value, nonce, deadline):
    """
    Generate permit data for EIP-2612
    """
    return {
        'owner': owner,
        'spender': spender,
        'value': value,
        'nonce': nonce,
        'deadline': deadline
    }

def build_permit_message(domain_data, permit_data):
    """
    Build the structured message for EIP-712 signing
    """
    return {
        'types': {
            'EIP712Domain': [
                {'name': 'name', 'type': 'string'},
                {'name': 'version', 'type': 'string'},
                {'name': 'chainId', 'type': 'uint256'},
                {'name': 'verifyingContract', 'type': 'address'}
            ],
            'Permit': [
                {'name': 'owner', 'type': 'address'},
                {'name': 'spender', 'type': 'address'},
                {'name': 'value', 'type': 'uint256'},
                {'name': 'nonce', 'type': 'uint256'},
                {'name': 'deadline', 'type': 'uint256'}
            ]
        },
        'primaryType': 'Permit',
        'domain': domain_data,
        'message': permit_data
    }

def generate_permit_signature(web3, private_key, token_name, token_address, chain_id, owner, spender, value, nonce, deadline=None):
    """
    Generate a signature for EIP-2612 permit function
    
    Args:
        web3: Web3 instance
        private_key: Private key of the owner
        token_name: Name of the token
        token_address: Address of the token contract
        chain_id: Chain ID of the network
        owner: Address of the token owner
        spender: Address of the spender (usually the relayer contract)
        value: Amount to approve
        nonce: Current nonce from the token contract
        deadline: Timestamp until which the signature is valid (default: 1 hour from now)
    
    Returns:
        Dictionary with signature components (v, r, s)
    """
    if deadline is None:
        deadline = int(time.time() + 3600)  # 1 hour from now
    
    domain_data = get_domain_data(token_name, token_address, chain_id)
    permit_data = get_permit_data(owner, spender, value, nonce, deadline)
    message = build_permit_message(domain_data, permit_data)
    
    # Sign the message
    account = Account.from_key(private_key)
    signed_message = Account.sign_typed_data(account, message)
    
    return {
        'v': signed_message.v,
        'r': signed_message.r,
        's': signed_message.s,
        'deadline': deadline
    }

def recover_signer(web3, token_name, token_address, chain_id, owner, spender, value, nonce, deadline, signature):
    """
    Recover the signer of a permit signature
    
    Args:
        web3: Web3 instance
        token_name: Name of the token
        token_address: Address of the token contract
        chain_id: Chain ID of the network
        owner: Address of the token owner
        spender: Address of the spender
        value: Amount approved
        nonce: Nonce used in the signature
        deadline: Timestamp until which the signature is valid
        signature: Dictionary with signature components (v, r, s)
    
    Returns:
        Address of the signer
    """
    domain_data = get_domain_data(token_name, token_address, chain_id)
    permit_data = get_permit_data(owner, spender, value, nonce, deadline)
    message = build_permit_message(domain_data, permit_data)
    
    # Recover the signer
    return Account.recover_typed_data(message, signature) 