import json
import time
from crypto_utils import encrypt_price, verify_signature

# Original Inventory
INVENTORY = {
    "Grocery": {
        "Organic Milk": 5,
        "Bread": 3,
        "Apples (1kg)": 4
    },
    "Accessories": {
        "Wireless Mouse": 25,
        "Keyboard": 45,
        "Laptop Sleeve": 15
    }
}

def verify_authority_token(token_data, public_key_hex):
    """
    Feature 5: Authority Tokens (Scoped Authorization)
    Verifies the token's signature, expiration, and integrity.
    """
    try:
        signature = token_data.get('signature')
        message = token_data.get('message') 
        
        is_valid = verify_signature(public_key_hex, message, signature)
        if not is_valid:
            return False, "Digital Signature Mismatch: Authority Denied."

        current_time = time.time()
        if current_time > message.get('expiry', 0):
            return False, "Authority Token has expired. Please issue a new one."

        return True, message
    except Exception as e:
        return False, f"Token Verification Error: {str(e)}"

def get_store_catalog():
    """Returns the catalog with all prices AES-encrypted (Feature 4)."""
    encrypted_catalog = {}
    for category, items in INVENTORY.items():
        encrypted_catalog[category] = {
            name: encrypt_price(price) for name, price in items.items()
        }
    return encrypted_catalog

def process_purchase_request(cart_items, token_data, public_key_hex):
    authorized, auth_payload = verify_authority_token(token_data, public_key_hex)
    if not authorized:
        return {"error": auth_payload}

    max_allowed_budget = auth_payload.get('max_budget', 0)
    results = []
    total_negotiated_price = 0
    
    for order in cart_items:
        item_name = order['item']
        user_ceiling = order['max_price'] # The user's "Do not exceed" limit ($54)
        quantity = order['quantity']
        
        # Find the internal store price
        real_price = 0
        for category, items in INVENTORY.items():
            if item_name in items:
                real_price = items[item_name]
                break
        
        # --- AUTONOMOUS AI AGENT LOGIC ---
        # 1. Define the Store's "Secret Floor" (15% discount)
        min_acceptable = real_price * 0.85
        
        # 2. Strategy: The Agent tries to get the LOWEST price possible ($38.25)
        # instead of the User's Max ($54).
        if user_ceiling >= min_acceptable:
            # SUCCESS: The Agent negotiated the price down to the store's minimum!
            # It chooses the minimum because it is an Autonomous Agent acting for the USER.
            final_price = min_acceptable 
            status = "success"
            log_msg = f"Agent Bargain: Price reduced to ${final_price}"
        else:
            # FAILURE: The Store's lowest price is still more than what the user authorized.
            final_price = 0
            status = "negotiating"
            log_msg = "Negotiation failed: Store floor is above user limit."

        if status == "success":
            item_total = round(final_price * quantity, 2)
            results.append({
                "item": item_name,
                "status": "success",
                "price_per_item": round(final_price, 2),
                "quantity": quantity,
                "total": item_total,
                "note": log_msg
            })
            total_negotiated_price += item_total
        else:
            results.append({
                "item": item_name,
                "status": "negotiating",
                "min_price": round(min_acceptable, 2),
                "quantity": quantity,
                "note": log_msg
            })
            
    final_total = round(total_negotiated_price, 2)

    # GUARDRAIL: Even if the individual items were cheap, does the TOTAL 
    # exceed the Authority Token budget?
    if final_total > max_allowed_budget:
        return {
            "status": "MFA_REQUIRED",
            "message": f"Agent Alert: Total ${final_total} exceeds signed budget of ${max_allowed_budget}.",
            "results": results,
            "total": final_total
        }

    return {"status": "APPROVED", "results": results, "total": final_total}
