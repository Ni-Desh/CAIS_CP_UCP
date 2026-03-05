import time

def create_authority_token(max_spend):
    # Simulating a scoped token (OAuth 2.1 concept)
    token = {
        "scope": f"spend_limit:{max_spend}",
        "expires": time.time() + 3600, # Valid for 1 hour
        "issuer": "Human_Boss"
    }
    return token

def ai_process_purchase(item_price, token):
    limit = int(token["scope"].split(":")[1])
    if item_price > limit:
        return False, "Budget Guardrail: Purchase exceeds limit!"
    return True, "Within budget."