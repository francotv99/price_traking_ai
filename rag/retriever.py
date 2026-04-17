"""Semantic retrieval from Qdrant and LLM-based answer generation."""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "conversational_query.txt"
_PROMPT_TEMPLATE = _PROMPT_PATH.read_text(encoding="utf-8")


class RAGRetriever:
    """Handles embedding generation, Qdrant search and LLM answer generation."""

    def __init__(
        self,
        qdrant_host: str,
        qdrant_port: int,
        qdrant_collection: str,
        openai_api_key: str,
        openai_api_key_for_llm: str | None = None,
        top_k: int = 5,
    ) -> None:
        self.qdrant_url = f"http://{qdrant_host}:{qdrant_port}"
        self.qdrant_collection = qdrant_collection
        self.openai_api_key = openai_api_key
        self.openai_llm_key = openai_api_key_for_llm or openai_api_key
        self.top_k = top_k

    async def query(self, product_id: str, question: str) -> tuple[str, list[str]]:
        """Answer a free-form question about a product using RAG."""
        async with httpx.AsyncClient(timeout=60) as client:
            query_vector = await self._embed(client, question)
            chunks = await self._search(client, product_id=product_id, vector=query_vector)

            if not chunks:
                return (
                    f"No hay información indexada para '{product_id}' en el corpus. "
                    "Ejecuta primero POST /rag/reindex para indexar el corpus del producto.",
                    [],
                )

            sources = [c["payload"].get("source", "unknown") for c in chunks]
            context = self._build_context(chunks)
            answer = await self._generate(client, product_id=product_id, question=question, context=context)
            return answer, list(dict.fromkeys(sources))

    async def _embed(self, client: httpx.AsyncClient, text: str) -> list[float]:
        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {self.openai_api_key}"},
            json={"input": text, "model": "text-embedding-ada-002"},
        )
        response.raise_for_status()
        return list(response.json()["data"][0]["embedding"])

    async def _search(self, client: httpx.AsyncClient, product_id: str, vector: list[float]) -> list[dict]:
        response = await client.post(
            f"{self.qdrant_url}/collections/{self.qdrant_collection}/points/search",
            json={
                "vector": vector,
                "limit": self.top_k,
                "with_payload": True,
                "filter": {
                    "must": [{"key": "product_id", "match": {"value": product_id}}]
                },
            },
        )
        response.raise_for_status()
        return list(response.json().get("result", []))

    async def _generate(self, client: httpx.AsyncClient, product_id: str, question: str, context: str) -> str:
        prompt = _PROMPT_TEMPLATE.format(
            product_id=product_id,
            question=question,
            retrieved_chunks=context,
        )
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.openai_llm_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 800,
            },
        )
        response.raise_for_status()
        return str(response.json()["choices"][0]["message"]["content"]).strip()

    @staticmethod
    def _build_context(chunks: list[dict]) -> str:
        lines: list[str] = []
        for i, chunk in enumerate(chunks, start=1):
            payload = chunk.get("payload", {})
            source = payload.get("source", "unknown")
            text = payload.get("text", "")
            lines.append(f"[{i}] Fuente: {source}\n{text}")
        return "\n\n".join(lines)
