# adapters.py
import httpx
import asyncio
import json
import time


class LLMAdapter:

    def __init__(self, api_key: str, url: str):
        self.api_key = api_key
        self.url = url

    async def post(self, payload: dict):

        async with httpx.AsyncClient(timeout=30) as client:
            return await client.post(
                self.url,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )