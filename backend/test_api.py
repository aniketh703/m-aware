"""
Smoke test for the Prescription API.
Runs the actual FastAPI app in-process via TestClient and exercises every endpoint.
"""
import json
from fastapi.testclient import TestClient
from main import app


def show(label, response):
    print(f"\n===== {label}  [HTTP {response.status_code}] =====")
    try:
        data = response.json()
        print(json.dumps(data, indent=2)[:1200])
    except Exception:
        print(response.text[:500])


with TestClient(app) as client:
    # 1. Health
    show("Health check", client.get("/health"))

    # 2. Exact match
    show("Exact lookup: 'Hapiron XT Tablet'",
         client.get("/medicine", params={"name": "Hapiron XT Tablet"}))

    # 3. Fuzzy match — lowercase + partial
    show("Fuzzy: 'hapiron'",
         client.get("/medicine", params={"name": "hapiron"}))

    # 4. Typo handling
    show("Typo: 'Dilcorr 60'",
         client.get("/medicine", params={"name": "Dilcorr 60"}))

    # 5. Search endpoint
    show("Search: q='cream' limit=3",
         client.get("/search", params={"q": "cream", "limit": 3}))

    # 6. Search by salt
    show("Search by salt: q='paracetamol'",
         client.get("/search", params={"q": "paracetamol", "limit": 3}))

    # 7. Garbage input
    show("Garbage input: 'xyzabc123'",
         client.get("/medicine", params={"name": "xyzabc123"}))

    # 8. Path-style 404
    show("Path 404: /medicine/Nonexistent",
         client.get("/medicine/Nonexistent"))

    # 9. List filtered by OTC
    show("List OTC (limit 3)",
         client.get("/medicines", params={"category": "otc", "limit": 3}))

    # 10. CORS preflight check
    r = client.get("/health", headers={"Origin": "http://example.com"})
    print(f"\n===== CORS check =====")
    print(f"access-control-allow-origin: {r.headers.get('access-control-allow-origin')}")

print("\n✅ All endpoint scenarios executed.")
