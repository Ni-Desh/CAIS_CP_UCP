import json
import os
from crypto_utils import sign_data, verify_signature, get_hash
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Setup keys for demonstration
if not os.path.exists("keys"): os.makedirs("keys")
if not os.path.exists("keys/user_private.key"):
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    with open("keys/user_private.key", "wb") as f:
        f.write(private_key.private_bytes(encoding=serialization.Encoding.Raw, format=serialization.PrivateFormat.Raw, encryption_algorithm=serialization.NoEncryption()))
    with open("keys/user_public.key", "wb") as f:
        f.write(public_key.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw))

# Load keys
with open("keys/user_private.key", "rb") as f: user_priv = f.read()
with open("keys/user_public.key", "rb") as f: user_pub = f.read()

print("--- STARTING UCP PROJECT WORKFLOW ---")

# ==========================================
# Step 1: User Instruction (The "Mandate")
# ==========================================
print("\n[Step 1] Creating Secure Mandate...")
mandate = {"item_requested": "Python Book", "max_price": 30}
mandate_sig = sign_data(mandate, user_priv)
print(f"✅ User signed mandate for max ${mandate['max_price']}")

# ==========================================
# Step 2: AI Searching & Bargaining (Mock)
# ==========================================
print("\n[Step 2] AI Searching & Bargaining...")
# AI finds book for $35, asks for discount, gets it for $28
final_price = 28
print(f"🤖 AI negotiated price to: ${final_price}")

# ==========================================
# Step 4: Execution & Guardrail Check
# ==========================================
print("\n[Step 4] Execution & Guardrail Check...")
# The store checks if the price is valid based on the signed mandate
if final_price <= mandate['max_price'] and verify_signature(mandate, mandate_sig, user_pub):
    print(f"✅ Guardrail Check Passed: ${final_price} <= ${mandate['max_price']}")
    
    # AI signs the actual purchase order
    purchase_order = {"item": "Python Book", "price": final_price}
    order_sig = sign_data(purchase_order, user_priv)
    print("✍️ AI Signed Final Order")
    
    # ==========================================
    # Step 5: Secure Audit Trail (The Output)
    # ==========================================
    print("\n[Step 5] Creating Secure Audit Trail...")
    receipt = {"order": purchase_order, "signature": order_sig.hex()}
    receipt_hash = get_hash(json.dumps(receipt))
    
    # Save to audit log
    if not os.path.exists("store"): os.makedirs("store")
    with open("store/audit.log", "a") as log:
        log.write(f"HASH: {receipt_hash} | DATA: {json.dumps(receipt)}\n")
        
    print(f"✅ Transaction Complete.")
    print(f"📜 Final Verification Hash: {receipt_hash[:20]}...")
else:
    print("❌ Critical Error: Guardrail Failed or Signature Invalid!")

print("\n--- PROJECT TASK COMPLETE ---")