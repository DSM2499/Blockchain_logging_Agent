import json
from web3 import Web3
import os
from dotenv import load_dotenv

load_dotenv()

#Environment Variables
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
WEB3_PROVIDER = os.getenv("WEB3_PROVIDER")
ABI_PATH = "agents/DecisionLoggerABI.json"
#Initialize Web3
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

try:
    if not w3.is_connected():
        raise Exception("Web3 connection failed")
        exit(1)

    with open(ABI_PATH) as f:
        abi = json.load(f)
        contract = w3.eth.contract(address = Web3.to_checksum_address(CONTRACT_ADDRESS), abi = abi)
        print(f"[LOG] Contract loaded successfully for address: {CONTRACT_ADDRESS}")
except Exception as e:
    raise Exception(f"Error loading ABI: {str(e)}")

# ------------------------------------------------------------
#Functions

def hash_data_consistantly(data_string: str) -> str:
    return w3.to_hex(w3.keccak(data_string.encode('utf-8')))

def get_all_logs(from_block: int = 0, to_block: int = 'latest') -> list:
    try:
        decision_events = contract.events.DecisionRecorded.get_logs(
            #fromBlock = 0,
            #toBlock = 'latest'
        )
        parsed_events = []
        for event in decision_events:
            parsed_events.append({
                'agent_id': event.args.agentid,
                'action': event.args.action,
                'reason_hash_on_chain': event.args.reasonhash.hex(),
                'timestamp_on_chain': event.args.timestamp,
                'transaction_hash': event.transactionHash.hex(),
                'block_number': event.blockNumber,
            })
        return parsed_events
    except Exception as e:
        print(f"🚨 Error fetching events: {e}")
        return []

def verify_log_entry(logged_reason_text: str, reason_hash_on_chain: str) -> bool:
    calculated_hash = hash_data_consistantly(logged_reason_text)
    print(f"[LOG] Calculated hash: {calculated_hash}")
    print(f"[LOG] On-chain hash: {reason_hash_on_chain}")
    return calculated_hash == reason_hash_on_chain

# ------------------------------------------------------------
#main
if __name__ == "__main__":
    print("Fetching recorded decisions...")
    decisions = get_all_logs()

    if not decisions:
        print("No decisions found on the blockchain.")
    else:
        for i, decision in enumerate(decisions):
            print(f"\n--- Decision Log Entry {i+1} ---")
            print(f"Agent ID: {decision['agent_id']}")
            print(f"Action: {decision['action']}")
            print(f"On-chain Reason Hash: {decision['reason_hash_on_chain']}")
            print(f"Transaction Hash: {decision['transaction_hash']}")
            print(f"Block Number: {decision['block_number']}")
            # In a real scenario, you'd fetch the full 'reason' text from off-chain storage (e.g., IPFS)
            # For demonstration, let's simulate a 'known' reason text that was logged.
            # You would replace this with actual retrieval logic.
            # For testing, you must provide the exact 'reason' string used when logging.
            sample_reason_for_verification = input(f"Enter the ORIGINAL reason text for Agent ID '{decision['agent_id']}' and Action '{decision['action']}' to verify (or leave blank to skip verification): ")

            if sample_reason_for_verification:
                is_verified = verify_log_entry(sample_reason_for_verification, decision['reason_hash_on_chain'])
                print(f"Verification Status: {'SUCCESS' if is_verified else 'FAILED'}")
                if not is_verified:
                    print("  !!! HASH MISMATCH: The provided reason text does not match the on-chain hash. !!!")
                    print("  This could be due to: inconsistent serialization (e.g., whitespace, field order), ")
                    print("  incorrect original text, or data corruption. Ensure exact match and encoding (UTF-8).")
            else:
                print("Verification skipped for this entry.")