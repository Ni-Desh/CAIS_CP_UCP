import json
import hashlib

def get_hash(data_string):
    return hashlib.sha512(data_string.encode()).hexdigest()

def verify_logs():
    try:
        with open("audit_log.json", "r") as f:
            logs = json.load(f)
        
        for i, entry in enumerate(logs):
            # 1. Take the data out, but hide the hash it came with
            stored_hash = entry.pop("transaction_hash")
            
            # 2. Re-calculate what the hash SHOULD be based on the current data
            # Use same formatting as app.py
            current_data_str = json.dumps(entry, sort_keys=True, separators=(',', ':'))
            calculated_hash = get_hash(current_data_str)
            
            # 3. Compare them
            if stored_hash == calculated_hash:
                print(f"✅ Entry {i}: VALID. Data matches hash.")
            else:
                print(f"❌ Entry {i}: TAMPERED! Hash does not match data.")
                print(f"   Stored: {stored_hash[:16]}...")
                print(f"   Actual: {calculated_hash[:16]}...")
                
    except Exception as e:
        print(f"Error reading logs: {e}")

if __name__ == "__main__":
    verify_logs()