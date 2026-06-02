import asyncio
import urllib.request
import json
import time

BASE_URL = "http://localhost:8000"

def api_request(path, method="GET", data=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    req_data = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, None

async def test_concurrent_logins():
    print("\n--- Test 1: Simultaneous Logins ---")
    users = [
        {"username": "superadmin", "password": "SA@2025!"},
        {"username": "admin", "password": "Adm@2025!"},
        {"username": "operario", "password": "Op@2025!"}
    ]
    
    loop = asyncio.get_event_loop()
    tasks = [loop.run_in_executor(None, api_request, "/login", "POST", u) for u in users]
    results = await asyncio.gather(*tasks)
    
    tokens = []
    for i, (status, body) in enumerate(results):
        if status == 200 and "access_token" in body:
            print(f"User {users[i]['username']} logged in successfully.")
            tokens.append(body["access_token"])
    return tokens

async def test_concurrent_inventory(token):
    print("\n--- Test 2: Simultaneous Inventory Queries ---")
    loop = asyncio.get_event_loop()
    tasks = [loop.run_in_executor(None, api_request, "/inventario", "GET", None, token) for _ in range(3)]
    results = await asyncio.gather(*tasks)
    for status, body in results:
        print(f"Status: {status}, Items count: {body.get('total_paquetes') if body else 'Error'}")

async def test_concurrent_orders(token):
    print("\n--- Test 3: Concurrent FIFO Allocation ---")
    orders = [{"codigo": f"PKG-CONF-{i}"} for i in range(5)]
    loop = asyncio.get_event_loop()
    tasks = [loop.run_in_executor(None, api_request, "/ordenar_paquete", "POST", o, token) for o in orders]
    results = await asyncio.gather(*tasks)
    
    positions = []
    for status, body in results:
        if status == 200:
            pos = body.get("asignacion_fifo")
            positions.append((pos["x"], pos["y"]))
    
    duplicates = len(positions) != len(set(positions))
    print(f"Orders placed: {len(positions)}. Duplicates found: {duplicates}")

async def test_security_failures():
    print("\n--- Test 4 & 5: Security Enforcement ---")
    # Test 4: No token
    status, _ = api_request("/inventario", "GET")
    print(f"Request without token status: {status} (Expected 401)")
    
    # Test 5: Invalid token
    status, _ = api_request("/inventario", "GET", token="invalid-token-xyz")
    print(f"Request with fake token status: {status} (Expected 401)")

async def main():
    print("Starting Concurrency and Security Tests...")
    tokens = await test_concurrent_logins()
    
    if tokens:
        await test_concurrent_inventory(tokens[0])
        await test_concurrent_orders(tokens[0])
    
    await test_security_failures()
    print("\nTests completed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Could not run tests: {e}. Is the server running at localhost:8000?")