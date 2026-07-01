import cognee
import inspect

print("Is serve in cognee?", hasattr(cognee, "serve"))
if hasattr(cognee, "serve"):
    print("serve signature:", inspect.signature(cognee.serve))
print("Is disconnect in cognee?", hasattr(cognee, "disconnect"))
