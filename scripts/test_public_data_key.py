from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.services.public_data import PublicDataClient


async def main() -> None:
    settings = get_settings()
    print(f"PUBLIC_DATA_SERVICE_KEY configured: {settings.has_public_data_key}")
    result = await PublicDataClient(settings).check_status()
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
