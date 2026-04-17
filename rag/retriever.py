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

    async def query(self, question: str, product_id: str | None = None) -> tuple[str, list[str], list[str]]:
        """Answer a free-form question, inferring one or more products from the question if not provided."""
        async with httpx.AsyncClient(timeout=60) as client:
            if product_id:
                resolved_ids = [product_id]
            else:
                resolved_ids = await self._extract_product_ids(client, question)

            if resolved_ids == ["unknown"]:
                return (
                    "No identifiqué ninguna criptomoneda en tu pregunta. "
                    "Prueba mencionando bitcoin, ethereum, solana o cardano.",
                    [],
                    ["unknown"],
                )

            query_vector = await self._embed(client, question)

            all_chunks: list[dict] = []
            missing: list[str] = []
            for pid in resolved_ids:
                chunks = await self._search(client, product_id=pid, vector=query_vector)
                if chunks:
                    all_chunks.extend(chunks)
                else:
                    missing.append(pid)

            if not all_chunks:
                return (
                    f"No hay información indexada para {resolved_ids} en el corpus. "
                    "Ejecuta primero POST /rag/reindex para indexar el corpus.",
                    [],
                    resolved_ids,
                )

            sources = list(dict.fromkeys(c["payload"].get("source", "unknown") for c in all_chunks))
            context = self._build_context(all_chunks)
            products_label = " y ".join(resolved_ids)
            answer = await self._generate(client, product_id=products_label, question=question, context=context)

            if missing:
                answer += f"\n\n⚠️ Sin datos indexados para: {', '.join(missing)}."

            return answer, sources, resolved_ids

    async def _extract_product_ids(self, client: httpx.AsyncClient, question: str) -> list[str]:
        """Infer one or more CoinGecko product IDs from a free-form question."""
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.openai_api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Extrae los IDs de CoinGecko de todas las criptomonedas mencionadas. "
                            "Responde SOLO con los IDs en minúsculas separados por coma, sin espacios. "
                            "Alias válidos: btc/BTC/Bitcoin → bitcoin, "
                            "eth/ETH/Ethereum/ether → ethereum, sol/SOL/Solana → solana, "
                            "ada/ADA/Cardano → cardano. "
                            "Ejemplo de múltiples: bitcoin,ethereum "
                            "Si no hay ninguna criptomoneda, responde exactamente: unknown"
                        ),
                    },
                    {"role": "user", "content": question},
                ],
                "temperature": 0,
                "max_tokens": 40,
            },
        )
        response.raise_for_status()
        raw = str(response.json()["choices"][0]["message"]["content"]).strip().lower()
        return [p.strip() for p in raw.split(",") if p.strip()]

    async def _embed(self, client: httpx.AsyncClient, text: str) -> list[float]:
        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {self.openai_api_key}"},
            json={"input": text, "model": "text-embedding-3-small"},
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
