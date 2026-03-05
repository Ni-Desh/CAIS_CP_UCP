import json
import os
from Crypto.Cipher import AES
from crypto_utils import generate_keys, sign_order, verify_signature, get_hash, STORE_KEY

# 1. Initialize System (Check for keys)
if not os.path.exists("keys/ai_private.key"):
    generate_keys()

print("--- AI CRYPTO PROJECT START ---")

# 2. Authority Token (Budget Guardrail)
budget_limit = 50
print(f" Authority Token Issued: Max Spend ${budget_limit}")

# 3. Decrypt Store Catalog (Symmetric Encryption)
# 
with open("store/ucp.bin", "rb") as f:
    nonce, tag, ciphertext = [f.read(x) for x in (16, 16, -1)]

cipher = AES.new(STORE_KEY, AES.MODE_GCM, nonce=nonce)
catalog = json.loads(cipher.decrypt_and_verify(ciphertext, tag))
print(f" Catalog Decrypted: Found {len(catalog['items'])} items.")

# 4. AI Selects Item & Signs (Digital Signature)
# --- UPDATED: AI Logic to select best item ---
selected_item = None
for item in catalog['items']:
    if item['price'] <= budget_limit:
        if selected_item is None or item['price'] > selected_item['price']:
            selected_item = item

if selected_item:
    print(f" AI Decision: Selecting '{selected_item['name']}' for ${selected_item['price']}")
    purchase_order = {"item": selected_item['name'], "price": selected_item['price']}

    # Load private key for signing
    with open("keys/ai_private.key", "rb") as f:
        priv_bytes = f.read()
        
    # 
    signature = sign_order(purchase_order, priv_bytes)
    print(f" AI Signed Order for {purchase_order['item']}")
    
    # 5. Store Verifies & Logs (Audit Trail)
    # Load public key for verification
    with open("keys/ai_public.key", "rb") as f:
        pub_bytes = f.read()
        
    if verify_signature(purchase_order, signature, pub_bytes):
        # --- UPDATED: Detailed Audit Logging ---
        # 
        receipt_hash = get_hash(f"{purchase_order}{signature.hex()}")
        with open("store/audit.log", "a") as log:
            log.write(f"--- NEW TRANSACTION ---\n")
            log.write(f"ORDER_DETAILS: {json.dumps(purchase_order)}\n")
            log.write(f"TX_HASH: {receipt_hash}\n\n")                
        
        print(f" Transaction Verified! Hash added to Audit Trail: {receipt_hash[:20]}...")
    else:
        print(" CRITICAL: Signature Verification Failed!")
else:
    print(" Guardrail Triggered: No items within budget!")

print("--- PROJECT TASK COMPLETE ---")