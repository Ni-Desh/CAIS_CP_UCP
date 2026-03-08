from flask import Flask, render_template, request, jsonify, session
import json, os, time, random, hashlib, hmac, secrets
from crypto_utils import sign_data, verify_signature, get_hash, get_session_key
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import store_api 

app = Flask(__name__)
app.secret_key = "ucp_secure_session_key_99" 

USER_DB = "users.json"
AUDIT_FILE = "audit_log.json" # New file for Feature 3
pending_otps = {}

def load_users():
    if not os.path.exists(USER_DB): return {}
    with open(USER_DB, "r") as f:
        try: return json.load(f)
        except: return {}

def save_users(users):
    with open(USER_DB, "w") as f:
        json.dump(users, f, indent=4)

def simple_hash(val):
    return hashlib.sha256(val.encode()).hexdigest()

# --- FEATURE 3: SECURE AUDIT LOGGING ---
def log_transaction(user, total, items):
    logs = []
    if os.path.exists(AUDIT_FILE):
        with open(AUDIT_FILE, "r") as f:
            try: logs = json.load(f)
            except: logs = []

    # Get hash of the last entry to chain them
    prev_hash = logs[-1]["transaction_hash"] if logs else "0" * 128

    new_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "user": user,
        "total": total,
        "items": items,
        "previous_hash": prev_hash
    }

    # Generate the SHA-512 Fingerprint
    entry_string = json.dumps(new_entry, sort_keys=True, separators=(',', ':'))
    new_entry["transaction_hash"] = get_hash(entry_string)

    logs.append(new_entry)
    with open(AUDIT_FILE, "w") as f:
        json.dump(logs, f, indent=4)
    return new_entry["transaction_hash"]

# --- NEW ROUTES FOR HACK SIMULATION & INTEGRITY CHECK ---

@app.route('/simulate-hack', methods=['POST'])
def simulate_hack():
    """Simulates a hacker manually editing the audit file."""
    print("--- Hack Simulation Triggered ---") # Check your terminal for this!
    if os.path.exists(AUDIT_FILE):
        try:
            with open(AUDIT_FILE, "r") as f:
                logs = json.load(f)
            
            if logs and len(logs) > 0:
                # Maliciously change the total of the VERY LAST transaction
                original_total = logs[-1]["total"]
                logs[-1]["total"] = 1.0 
                
                with open(AUDIT_FILE, "w") as f:
                    json.dump(logs, f, indent=4)
                
                print(f"DEBUG: Changed total from {original_total} to 1.0")
                return jsonify(log="🕵️ HACKER ALERT: Last transaction total changed to $1.00 in the audit file!")
            else:
                return jsonify(log="❌ Hack Failed: Audit log is empty. Make a purchase first!")
        except Exception as e:
            print(f"Error during hack: {e}")
            return jsonify(log=f"❌ Error: {str(e)}")
            
    return jsonify(log="❌ No logs found to hack. Make a purchase first.")

@app.route('/verify-integrity', methods=['POST'])
def verify_integrity():
    """Feature 3: Verifies all SHA-512 hashes in the audit trail."""
    if not os.path.exists(AUDIT_FILE):
        return jsonify(log="❌ No audit logs found.", status="error")
        
    with open(AUDIT_FILE, "r") as f:
        logs = json.load(f)
    
    for i, entry in enumerate(logs):
        # Temporarily extract the stored hash to re-calculate it
        stored_hash = entry.pop("transaction_hash")
        
        # Re-calculate hash using the EXACT same formatting as log_transaction
        entry_str = json.dumps(entry, sort_keys=True, separators=(',', ':'))
        calculated_hash = get_hash(entry_str)
        
        if stored_hash != calculated_hash:
            return jsonify(log=f"🚨 INTEGRITY FAILURE: Entry {i} has been tampered with!", status="fail")
            
    return jsonify(log="✅ INTEGRITY VERIFIED: All SHA-512 hashes match the data.", status="pass")

# -------------------------------------------------------

def get_keys():
    if not os.path.exists("keys"): os.makedirs("keys")
    if not os.path.exists("keys/user_private.key"):
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        with open("keys/user_private.key", "wb") as f:
            f.write(private_key.private_bytes(encoding=serialization.Encoding.Raw, format=serialization.PrivateFormat.Raw, encryption_algorithm=serialization.NoEncryption()))
        with open("keys/user_public.key", "wb") as f:
            f.write(public_key.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw))
    return open("keys/user_private.key", "rb").read(), open("keys/user_public.key", "rb").read()

@app.route('/')
def home(): return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    users = load_users()
    username, password, phone = data.get('username'), data.get('password'), data.get('phone')
    if not username or not password or not phone: return jsonify({"error": "Missing fields"}), 400
    users[username] = {"password_hash": simple_hash(password), "phone": phone}
    save_users(users)
    return jsonify({"status": "success"})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    users = load_users()
    user = users.get(data.get('username'))
    if user and hmac.compare_digest(user['password_hash'], simple_hash(data.get('password'))):
        session.clear()
        session['user'], session['phone'] = data.get('username'), user['phone']
        return jsonify({"status": "success", "username": data.get('username')})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/catalog')
def get_catalog(): return jsonify(store_api.get_store_catalog())

@app.route('/generate-token', methods=['POST'])
def generate_token():
    user_priv, _ = get_keys()
    data = request.json
    token_data = {
        "user_id": str(session.get('user', 'guest')),
        "max_budget": int(float(data.get('limit', 100))),
        "expiry": int(time.time() + 1800),
        "nonce": str(secrets.token_hex(8)) 
    }
    return jsonify({"token": token_data, "signature": sign_data(token_data, user_priv)})

@app.route('/get-catalog-key', methods=['POST'])
def provide_key():
    data = request.json
    _, user_pub = get_keys()
    if verify_signature(user_pub.hex(), data.get('auth_token'), data.get('auth_signature')):
        return jsonify({"key": get_session_key()})
    return jsonify({"error": "Unauthorized"}), 403

@app.route('/propose', methods=['POST'])
def propose():
    data = request.json
    _, user_pub = get_keys()
    token_data = {"message": data.get('token'), "signature": data.get('signature')}
    
    store_response = store_api.process_purchase_request(data.get('cart', []), token_data, user_pub.hex())
    
    if "error" in store_response:
        return jsonify(log=f"❌ Authority Error: {store_response['error']}", status="error"), 403

    return jsonify(
        log="Negotiation complete - Scoped Authority Verified", 
        provisional_order=store_response["results"], 
        total=store_response["total"],
        status=store_response.get("status")
    )

@app.route('/request-otp', methods=['POST'])
def request_otp():
    user, phone = session.get('user'), session.get('phone', 'Unknown')
    raw_otp = str(random.randint(100000, 999999))
    pending_otps[user] = {"hash": simple_hash(raw_otp), "expiry": time.time() + 300}
    print(f"\n [SMS] To {phone}: Code is {raw_otp}\n")
    return jsonify({"status": "sent"})

@app.route('/pay', methods=['POST'])
def pay():
    data = request.json
    user = session.get('user')
    _, user_pub = get_keys()
    
    if not verify_signature(user_pub.hex(), data.get('auth_token'), data.get('auth_signature')):
        return jsonify(log="❌ Signature Error", status="error")
    
    order = data.get('order', [])
    total = sum(item.get('total', 0) for item in order)
    items_list = [item.get('item') for item in order]

    tx_hash = log_transaction(user, total, items_list)

    return jsonify({
        "log": f"✅ Transaction Securely Signed.\n Audit Hash: {tx_hash[:16]}...",
        "status": "success"
    })

if __name__ == '__main__':
    app.run(debug=True)
