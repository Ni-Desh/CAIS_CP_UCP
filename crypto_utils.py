import hashlib
import json
import base64
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# 32-byte key for AES-256 Catalog Encryption (Feature 4)
CATALOG_KEY = b'12345678901234567890123456789012' 

def get_session_key():
    return base64.b64encode(CATALOG_KEY).decode()

def encrypt_price(price):
    """Symmetric Encryption (AES-256) for Catalog Prices."""
    iv = b'\x00' * 16 
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(str(price).encode()) + padder.finalize()
    cipher = Cipher(algorithms.AES(CATALOG_KEY), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ct = encryptor.update(padded_data) + encryptor.finalize()
    return base64.b64encode(ct).decode()

def sign_data(data, private_key_bytes):
    """Feature 1: Ed25519 Digital Signing."""
    priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    # separators=(',', ':') removes all whitespace for bit-perfect matching
    message = json.dumps(data, sort_keys=True, separators=(',', ':')).encode()
    return priv_key.sign(message).hex()

def verify_signature(public_key, data, signature_hex):
    """
    Feature 1: Digital Signature Verification.
    Corrected to handle public_key as Hex String and data as Dict/String.
    """
    try:
        # Convert public_key from hex string to bytes if necessary
        if isinstance(public_key, str):
            public_key_bytes = bytes.fromhex(public_key)
        else:
            public_key_bytes = public_key

        pub_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
        
        # Ensure the message is formatted EXACTLY as it was when signed
        if isinstance(data, dict):
            message = json.dumps(data, sort_keys=True, separators=(',', ':')).encode()
        else:
            message = data.encode() if isinstance(data, str) else data
            
        pub_key.verify(bytes.fromhex(signature_hex), message)
        return True
    except Exception as e:
        print(f"❌ Signature Verification Failed: {e}")
        return False

def get_hash(data_string):
    """Feature 3: SHA-512 Hashing for Audit Logs."""
    return hashlib.sha512(data_string.encode()).hexdigest()