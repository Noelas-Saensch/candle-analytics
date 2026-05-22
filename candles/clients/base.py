import httpx


class BaseClient:
    def __init__(self, base_url: str, timeout: float = 15.0):
        self._http = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout)

    async def _get(self, path: str, params: dict | None = None):
        resp = await self._http.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        await self._http.aclose()
