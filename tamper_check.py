import json
from crypto_utils import get_hash

def check_audit_log():
    print("---  RUNNING AUDIT LOG INTEGRITY CHECK 🛡️ ---")
    
    # 1. Read the current audit log
    with open("store/audit.log", "r") as log:
        lines = log.readlines()
        
    # Find the last transaction
    last_tx_hash = lines[-2].split(": ")[1].strip()
    
    print(f"Original Hash from Log: {last_tx_hash[:20]}...")
    
    # 2. SIMULATE TAMPERING (Hacker changes price from 40 to 5)
    # Note: In a real scenario, the hacker would try to modify the logged JSON string
    tampered_order = {"item": "GPU Cloud Credits", "price": 5}
    
    # Note: A clever hacker would need the signature to change the hash...
    # For this simulation, we check if changing the price creates a new hash.                
    new_hash = get_hash(f"{tampered_order}")
    
    print(f"Computed Hash of Tampered Data: {new_hash[:20]}...")
    
    # 3. VERIFY
    if last_tx_hash == new_hash:
        print(" Log Integrity Verified (No tampering detected)")
    else:
        print(" CRITICAL: TAMPERING DETECTED! Log hash does not match data.")

if __name__ == "__main__":
    check_audit_log()