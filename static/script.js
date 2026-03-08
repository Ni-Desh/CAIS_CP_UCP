// --- STATE MANAGEMENT ---
let currentUser = null;
let isSignup = false;
let cart = [];
let catalogSessionKey = null; 
let currentAuthToken = null;
let currentAuthSignature = null;
let negotiatedTotal = 0;
let currentProvisionalOrder = null;
let userSetLimit = 0;

// --- AUTH UI LOGIC ---

function toggleAuth() {
    isSignup = !isSignup;
    const title = document.getElementById('auth-title');
    const phoneBox = document.getElementById('phone-box');
    const authBtn = document.getElementById('auth-btn');
    const toggleLink = document.getElementById('toggle-link');

    if (isSignup) {
        title.innerText = "📝 Create Account";
        phoneBox.style.display = "block";
        authBtn.innerText = "Sign Up";
        toggleLink.innerText = "Already have an account? Login";
    } else {
        title.innerText = "🔐 UCP Login";
        phoneBox.style.display = "none";
        authBtn.innerText = "Login";
        toggleLink.innerText = "Don't have an account? Sign Up";
    }
}

async function handleAuth() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const phone = document.getElementById('phone').value;
    
    if (!username || !password) {
        alert("Please enter both username and password.");
        return;
    }

    const url = isSignup ? '/signup' : '/login';
    const payload = { username, password };
    if (isSignup) payload.phone = phone;

    try {
        const res = await fetch(url, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        
        if (res.ok) {
            if (isSignup) {
                alert("Account created! Please login.");
                toggleAuth();
            } else { 
                currentUser = data.username;
                document.getElementById('auth-screen').style.display = 'none';
                document.getElementById('main-app').style.display = 'block';
                document.getElementById('user-tag').innerText = "👤 User: " + currentUser;
                loadCatalog(); 
            }
        } else {
            alert(data.error || "Authentication failed.");
        }
    } catch (e) {
        console.error("Auth error:", e);
    }
}

// --- CATALOG & CART LOGIC ---

async function loadCatalog() {
    try {
        const response = await fetch('/catalog');
        const data = await response.json();
        const catDiv = document.getElementById('catalog');
        catDiv.innerHTML = '';

        for (const [cat, items] of Object.entries(data)) {
            catDiv.innerHTML += `<h3 style="grid-column: 1 / -1; margin-top: 15px; border-bottom: 1px solid #eee;">${cat}</h3>`;
            for (const [name, priceEnc] of Object.entries(items)) {
                let displayPrice = priceEnc;
                let locked = true;

                if (catalogSessionKey) {
                    try {
                        const key = CryptoJS.enc.Base64.parse(catalogSessionKey);
                        const iv = CryptoJS.enc.Hex.parse('00000000000000000000000000000000');
                        const dec = CryptoJS.AES.decrypt(priceEnc, key, {iv: iv, mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7});
                        const decryptedStr = dec.toString(CryptoJS.enc.Utf8);
                        if (decryptedStr) {
                            displayPrice = parseFloat(decryptedStr);
                            locked = false;
                        }
                    } catch (e) { console.error("Decryption error", e); }
                }

                catDiv.innerHTML += `
                    <div class="item-card" onclick="addToCart('${name}', ${locked ? `'${priceEnc}'` : displayPrice})">
                        <strong>${name}</strong> <br> 
                        <span style="color:${locked ? '#e74c3c' : '#27ae60'}">
                            ${locked ? '🔒 Encrypted' : '$' + displayPrice.toFixed(2)}
                        </span>
                    </div>`;
            }
        }
    } catch (e) { console.error("Catalog load error:", e); }
}

function addToCart(name, price) {
    if (typeof price !== 'number') {
        alert("🔒 Please unlock the catalog with an Authority Token first!");
        return;
    }
    const item = cart.find(i => i.item === name);
    if (item) {
        item.quantity++;
    } else {
        cart.push({ item: name, market_price: price, max_price: price * 1.2, quantity: 1 });
    }
    renderCart();
}

function updateQuantity(name, delta) {
    const item = cart.find(i => i.item === name);
    if (item) {
        item.quantity += delta;
        if (item.quantity <= 0) cart = cart.filter(i => i.item !== name);
    }
    renderCart();
}

function renderCart() {
    const div = document.getElementById('cart-items');
    const processBtn = document.getElementById('process-btn');

    if (cart.length === 0) {
        div.innerHTML = '<p style="text-align:center; color:#95a5a6; padding:10px;">Your cart is empty.</p>';
        processBtn.disabled = true;
        document.getElementById('payment-panel').style.display = 'none';
        return;
    }

    processBtn.disabled = false;

    div.innerHTML = cart.map(i => `
        <div class="cart-row" style="display:flex; align-items:center; justify-content:space-between; padding: 10px 0; border-bottom:1px solid #eee;">
            <div style="flex: 2;">
                <div style="font-weight:bold;">${i.item}</div>
                <div style="font-size: 0.8em; color:#7f8c8d;">$${i.market_price.toFixed(2)} / unit</div>
            </div>
            
            <div style="flex: 1.5; display: flex; align-items:center; justify-content: center; gap: 8px;">
                <button onclick="updateQuantity('${i.item}', -1)" style="width:28px; height:28px; cursor:pointer; border:1px solid #333; background:#eee; color:#000; font-weight:bold; display:flex; align-items:center; justify-content:center;">-</button>
                <span style="font-weight:bold; min-width: 25px; text-align:center; color:#333;">${i.quantity}</span>
                <button onclick="updateQuantity('${i.item}', 1)" style="width:28px; height:28px; cursor:pointer; border:1px solid #333; background:#eee; color:#000; font-weight:bold; display:flex; align-items:center; justify-content:center;">+</button>
            </div>
            
            <div style="flex: 1; text-align: right; font-weight: bold; color: #2c3e50;">
                $${(i.market_price * i.quantity).toFixed(2)}
            </div>
        </div>
    `).join('');
}

// --- AUTHORITY & WORKFLOW ---

async function requestAuthority() {
    const limitInput = prompt("Enter Authorized Budget ($):", "100");
    if (!limitInput) return;
    
    userSetLimit = parseInt(limitInput); 
    
    try {
        const res = await fetch('/generate-token', {
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify({limit: userSetLimit})
        });
        const d = await res.json();
        
        currentAuthToken = d.token; 
        currentAuthSignature = d.signature;
        
        const kRes = await fetch('/get-catalog-key', {
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify({
                auth_token: currentAuthToken, 
                auth_signature: currentAuthSignature
            })
        });
        const kData = await kRes.json();
        
        if (kData.key) {
            catalogSessionKey = kData.key;
            document.getElementById('log').innerText += `\n✅ Authority Token Valid. Budget Limit: $${userSetLimit}`;
            loadCatalog(); 
        } else {
            alert("Authority Denied: Digital Signature Mismatch.");
        }
    } catch (e) { console.error("Auth error:", e); }
}

async function runWorkflow() {
    const logBox = document.getElementById('log');

    if (!currentAuthToken || !currentAuthSignature) {
        alert("🔒 Authority Error: No signed token found. Click 'Get Authority' first.");
        logBox.innerText += `\n❌ Negotiation Failed: Missing Authority Token.`;
        return;
    }

    logBox.innerText += `\n🤖 AI Agent: Initiating Scoped Negotiation...`;

    try {
        const res = await fetch('/propose', {
            method: 'POST', 
            headers: {'Content-Type': 'application/json'}, 
            body: JSON.stringify({
                cart: cart,
                token: currentAuthToken,
                signature: currentAuthSignature
            })
        });
        const data = await res.json();

        if (data.status === "error") {
            logBox.innerText += `\n${data.log}`;
            alert(data.log);
            return;
        }
        
        // AI Bargaining Log for UI Console
        data.provisional_order.forEach(item => {
            let originalItemTotal = cart.find(c => c.item === item.item).market_price * item.quantity;
            logBox.innerText += `\n Negotiated ${item.item} (x${item.quantity}): $${originalItemTotal.toFixed(2)} ➔ $${item.total.toFixed(2)}`;
        });
        
        negotiatedTotal = data.total; 
        currentProvisionalOrder = data.provisional_order;
        
        document.getElementById('payment-panel').style.display = 'block';
        document.getElementById('payment-details').innerHTML = `
            <div style="background:#f8f9fa; padding:10px; border-radius:5px; border-left: 4px solid ${data.status === 'MFA_REQUIRED' ? '#e74c3c' : '#27ae60'};">
                <p>Total: <strong>$${negotiatedTotal.toFixed(2)}</strong> (Limit: $${userSetLimit})</p>
                <p style="color:${data.status === 'MFA_REQUIRED' ? '#e74c3c' : '#27ae60'};">
                    ${data.status === 'MFA_REQUIRED' ? '⚠️ OTP Required (Budget Exceeded)' : '✅ Budget Verified'}
                </p>
            </div>`;
            
        logBox.scrollTop = logBox.scrollHeight;
    } catch (e) { console.error("Negotiation error:", e); }
}

async function confirmPayment() {
    const logBox = document.getElementById('log');
    let otp = null;
    if (negotiatedTotal > userSetLimit) {
        alert("Budget Guardrail Tripped! SMS code sent.");
        await fetch('/request-otp', {method: 'POST', headers: {'Content-Type': 'application/json'}});
        otp = prompt("📱 Enter the 6-digit SMS code:");
        if (!otp) return;
    }

    try {
        const res = await fetch('/pay', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                order: currentProvisionalOrder,
                auth_token: currentAuthToken,
                auth_signature: currentAuthSignature,
                otp: otp
            })
        });
        
        const data = await res.json();
        logBox.innerText += "\n" + data.log;
        
        if (data.status === "success") { 
            cart = []; 
            renderCart(); 
            document.getElementById('payment-panel').style.display = 'none'; 
            alert("Success!");
        } else {
            alert("Error: " + data.log);
        }
        logBox.scrollTop = logBox.scrollHeight;
    } catch (e) { console.error("Payment error:", e); }
}

async function simulateHack() {
    const logBox = document.getElementById('log');
    try {
        const res = await fetch('/simulate-hack', { method: 'POST' });
        const data = await res.json();
        logBox.innerText += `\n${data.log}`;
        alert("HACK SIMULATED: The database file has been tampered with!");
        logBox.scrollTop = logBox.scrollHeight;
    } catch (e) { console.error("Hack simulation error:", e); }
}

async function verifyIntegrity() {
    const logBox = document.getElementById('log');
    try {
        const res = await fetch('/verify-integrity', { method: 'POST' });
        const data = await res.json();
        
        if (data.status === "fail") {
            logBox.innerHTML += `\n<span style="color:#e74c3c; font-weight:bold;">${data.log}</span>`;
            alert("🚨 SECURITY ALERT: Tampering detected!");
        } else if (data.status === "pass") {
            logBox.innerHTML += `\n<span style="color:#27ae60; font-weight:bold;">${data.log}</span>`;
            alert("✅ System Integrity Confirmed.");
        } else {
            logBox.innerText += `\n${data.log}`;
        }
        logBox.scrollTop = logBox.scrollHeight;
    } catch (e) { console.error("Integrity check error:", e); }
}

// --- ATTACH TO WINDOW ---
window.handleAuth = handleAuth; 
window.toggleAuth = toggleAuth; 
window.requestAuthority = requestAuthority;
window.runWorkflow = runWorkflow; 
window.confirmPayment = confirmPayment;
window.addToCart = addToCart;
window.updateQuantity = updateQuantity;
window.simulateHack = simulateHack; 
window.verifyIntegrity = verifyIntegrity;
