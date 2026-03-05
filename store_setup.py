from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import json
import os
from crypto_utils import STORE_KEY

# Example Catalog
catalog = {
    "items": [
        {"id": 1, "name": "GPU Cloud Credits", "price": 40},
        {"id": 2, "name": "Data Dataset", "price": 15}
    ]
}

def encrypt_catalog(data):
    # Ensure folder exists
    os.makedirs("store", exist_ok=True)
    
    cipher = AES.new(STORE_KEY, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(json.dumps(data).encode())
    
    with open("store/ucp.bin", "wb") as f:
        [f.write(x) for x in (cipher.nonce, tag, ciphertext)]
    print("✅ Catalog encrypted and saved to store/ucp.bin!")

if __name__ == "__main__":
    encrypt_catalog(catalog)