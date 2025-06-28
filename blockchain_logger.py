import json
import hashlib
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from web3 import Web3
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv

load_dotenv()

#Configuration
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
WEB3_PROVIDER = os.getenv("WEB3_PROVIDER")
ACCOUNT_ADDRESS = os.getenv("ACCOUNT_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ABI_PATH = "DecisionLoggerABI.json"

#Loading Smart Contract
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

if not w3.is_connected():
    raise Exception("Web3 connection failed")
    exit(1)

try:
    with open(ABI_PATH) as f:
        abi = json.load(f)
        contract = w3.eth.contract(address = Web3.to_checksum_address(CONTRACT_ADDRESS), abi = abi)
        print(f"[LOG] Contract loaded successfully for address: {CONTRACT_ADDRESS}")
except Exception as e:
    raise Exception(f"Error loading ABI: {str(e)}")
    exit(1)

# ------------------------------------------------------------
#FastAPI App

app = FastAPI(
    title = "Blockchain Logging Agent",
    description = "A plug-and-play module to track decisions and reasoning of AI agents on a blockchain.",
    version = "0.1.0"
)

class DecisionInput(BaseModel):
    agent_id: str
    action: str
    reason: str
    timestamp: Optional[str] = None

    def model_post_init(self, __context: Any):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

#Core functions
def hash_data_consistantly(data_string: str) -> str:
    return w3.to_hex(w3.keccak(data_string.encode('utf-8')))

def log_to_blockchain(agent_id: str, action: str, reason_hash: str) -> str:
    try:
        nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)

        # Ensure your Solidity contract looks something like:
        # function recordDecision(string memory _agentId, string memory _action, bytes32 _reasonHash) public { ... }
        txn = contract.functions.recordDecision(agent_id, action, Web3.to_bytes(hexstr = reason_hash)).build_transaction({
            'from': ACCOUNT_ADDRESS,
            'nonce': nonce,
            'gas': 2000000,
            'gasPrice': w3.to_wei('50', 'gwei')
        })
        print(f"[INFO] Transaction built. Nonce: {nonce}")

        signed_txn  =w3.eth.account.sign_transaction(txn, private_key = PRIVATE_KEY)
        print(f"[INFO] Transaction signed. Sending to network...")

        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print(f"[INFO] Transaction sent. Waiting for receipt...")
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"[INFO] Transaction confirmed. Receipt: {receipt}")
        
        return receipt.transactionHash.hex()
    
    except Exception as e:
        print(f"[ERROR] Failed to log decision: {str(e)}")
        raise

# ------------------------------------------------------------
#API Endpoints

@app.post("/log", summary = "Log a decision to the blockchain")
async def log_decision(decision: DecisionInput):
    try:
        print(f"[LOG] Received input: {decision.dict()}")

        reason_hash = hash_data_consistantly(decision.reason)
        print(f"[LOG] Hashed reason: {reason_hash}")

        tx_hash = log_to_blockchain(decision.agent_id, decision.action, reason_hash)
        print(f"[LOG] Blockchain TX successful: {tx_hash}")

        return {
            "status": "success",
            "message": "Decision logged successfully.",
            "tx_hash": tx_hash,
            "reason_hash": reason_hash,
            "logged_data": decision.dict() # Return the full logged data for confirmation
        }
    except Exception as e:
        print(f"🚨 Exception during logging: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health", summary = "Check the health of the API")
def health():
    return {"status": "ok", "web3_connected": w3.is_connected()}

# ------------------------------------------------------------