#!/usr/bin/env python3
"""Create or reset the Scanix test account, then print a summary banner.

Run inside the backend container (WORKDIR /app, PYTHONPATH=/app):
    docker compose -f docker-compose.netlab.yml exec -T -e PYTHONPATH=/app \
        backend python3 scripts/create_test_account.py
"""

import asyncio

from app.core.database import async_session
from app.services.seed import create_or_reset_test_account, banner


async def _main() -> None:
    async with async_session() as db:
        info = await create_or_reset_test_account(db)
    print(banner(info))


if __name__ == "__main__":
    asyncio.run(_main())
