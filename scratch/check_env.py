import os
print("--- Env Variables Check ---")
for k, v in os.environ.items():
    if "COGNEE" in k or "GEMINI" in k or "ONEIROS" in k or "API_KEY" in k:
        print(f"{k} = {v[:10]}... (len={len(v)})" if len(v) > 10 else f"{k} = {v}")
print("---------------------------")
