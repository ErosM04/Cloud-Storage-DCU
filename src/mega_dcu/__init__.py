import asyncio
import types

# Compatibility shim for Python 3.11+ with tenacity < 6.0 (required by mega.py)
if not hasattr(asyncio, 'coroutine'):
    asyncio.coroutine = types.coroutine
