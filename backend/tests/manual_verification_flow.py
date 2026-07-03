import asyncio
import httpx
import sys
import time

BASE_URL = "http://127.0.0.1:8000/api"

async def run_verification():
    print("==================================================")
    # Step 1: Wipe database
    print("[1/9] Resetting database...")
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            res = await client.post(f"{BASE_URL}/debug/reset")
            res.raise_for_status()
            print(f"      Response: {res.json()}")
        except Exception as e:
            print(f"[ERROR] Failed to reset database: {e}")
            sys.exit(1)

        # Step 2: Ingest initial fact
        print("\n[2/9] Ingesting initial fact: 'My name is Nandu'...")
        try:
            res = await client.post(f"{BASE_URL}/chat", json={"message": "My name is Nandu"})
            res.raise_for_status()
            print(f"      Response: {res.json()}")
        except Exception as e:
            print(f"[ERROR] Failed to ingest initial fact: {e}")
            sys.exit(1)

        # Step 3: Verify initial status in memory mirror
        print("\n[3/9] Verifying initial raw status in mirror...")
        try:
            res = await client.get(f"{BASE_URL}/chat/memories")
            res.raise_for_status()
            nodes = res.json().get("nodes", [])
            print(f"      Found {len(nodes)} nodes in mirror.")
            for node in nodes:
                print(f"        - Node: '{node['content']}' | Status: {node['metadata'].get('status')} | Metadata: {node['metadata']}")
        except Exception as e:
            print(f"[ERROR] Failed to retrieve memories: {e}")
            sys.exit(1)

        # Step 4: Run first sleep cycle
        print("\n[4/9] Triggering first sleep cycle...")
        try:
            res = await client.post(f"{BASE_URL}/sleep/start")
            res.raise_for_status()
            print(f"      Sleep response: {res.json()}")
        except Exception as e:
            print(f"[ERROR] Failed to trigger sleep: {e}")
            sys.exit(1)

        # Poll sleep status until done
        print("      Polling sleep status...")
        while True:
            res = await client.get(f"{BASE_URL}/sleep/status")
            status = res.json().get("status")
            print(f"      Current sleep status: {status}")
            if status != "dreaming":
                break
            await asyncio.sleep(2.0)

        # Step 5: Verify consolidated nodes
        print("\n[5/9] Checking nodes in mirror post first sleep...")
        try:
            res = await client.get(f"{BASE_URL}/chat/memories")
            nodes = res.json().get("nodes", [])
            for node in nodes:
                print(f"        - Node: '{node['content']}' | Status: {node['metadata'].get('status')} | Metadata: {node['metadata']}")
        except Exception as e:
            print(f"[ERROR] Failed to check post-sleep memories: {e}")
            sys.exit(1)

        # Step 6: Ingest conflicting fact
        print("\n[6/9] Ingesting conflicting fact: 'Actually my name is Rithvik'...")
        try:
            res = await client.post(f"{BASE_URL}/chat", json={"message": "Actually my name is Rithvik"})
            res.raise_for_status()
            print(f"      Response: {res.json()}")
        except Exception as e:
            print(f"[ERROR] Failed to ingest conflicting fact: {e}")
            sys.exit(1)

        # Step 7: Run second sleep cycle
        print("\n[7/9] Triggering second sleep cycle for conflict resolution...")
        try:
            res = await client.post(f"{BASE_URL}/sleep/start")
            res.raise_for_status()
            print(f"      Sleep response: {res.json()}")
        except Exception as e:
            print(f"[ERROR] Failed to trigger sleep: {e}")
            sys.exit(1)

        print("      Polling sleep status...")
        while True:
            res = await client.get(f"{BASE_URL}/sleep/status")
            status = res.json().get("status")
            print(f"      Current sleep status: {status}")
            if status != "dreaming":
                break
            await asyncio.sleep(2.0)

        # Step 8: Verify conflict resolution status and edges in memory mirror
        print("\n[8/9] Verifying conflict resolution status and nodes in mirror...")
        try:
            res = await client.get(f"{BASE_URL}/chat/memories")
            nodes = res.json().get("nodes", [])
            for node in nodes:
                print(f"        - Node ID: {node['id']} | Content: '{node['content']}' | Status: {node['metadata'].get('status')} | Metadata: {node['metadata']}")
            
            # Fetch graph edges
            res_graph = await client.get(f"{BASE_URL}/graph")
            edges = res_graph.json().get("edges", [])
            print(f"      Edges in current graph:")
            for edge in edges:
                print(f"        - Edge: {edge['source']} --({edge['type']})--> {edge['target']}")
        except Exception as e:
            print(f"[ERROR] Failed to retrieve post-resolution graph: {e}")
            sys.exit(1)

        # Step 9: Ask "Who am I?"
        print("\n[9/9] Querying agent: 'Who am I?'...")
        try:
            res = await client.post(f"{BASE_URL}/chat", json={"message": "Who am I?"})
            res.raise_for_status()
            print("==================================================")
            print(f"  ANSWER: {res.json().get('response')}")
            print("==================================================")
        except Exception as e:
            print(f"[ERROR] Failed to query who am i: {e}")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_verification())
