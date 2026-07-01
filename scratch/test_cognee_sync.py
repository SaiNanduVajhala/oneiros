import cognee
import inspect
import asyncio

print("Is serve coroutine?", inspect.iscoroutinefunction(cognee.serve))
print("Is disconnect coroutine?", inspect.iscoroutinefunction(cognee.disconnect))
