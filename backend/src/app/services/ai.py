"""AI model service - handles inference, streaming, and model management."""
from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

from app.config.settings import get_settings
from app.core.exceptions import ModelError
from app.core.logging import get_logger
from app.schemas import ChatCompletionRequest, ChatMessage, EmbeddingRequest, EmbeddingResponse, StreamEvent

logger = get_logger(__name__)


class ModelProvider:
    """Base interface for AI model providers."""

    def __init__(self, base_url: str, default_model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Make a chat completion request."""
        raise NotImplementedError

    async def generate_embedding(self, text: str, model: str | None = None) -> list[float]:
        """Generate an embedding vector."""
        raise NotImplementedError

    async def list_models(self) -> list[dict[str, Any]]:
        """List available models."""
        raise NotImplementedError

    async def stream_completion(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream completion response as JSON chunks."""
        raise NotImplementedError


class OllamaProvider(ModelProvider):
    """Ollama-compatible model provider (Ollama, llama.cpp, MLX)."""

    def __init__(self, base_url: str = "http://localhost:11434", default_model: str = "qwen2.5-coder:7b") -> None:
        super().__init__(base_url, default_model)

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Chat completion via Ollama API."""
        import httpx

        settings = get_settings()
        model = model or self.default_model
        url = f"{self.base_url}/api/chat"

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            raise ModelError(f"Ollama request failed: {e.response.status_code} - {e.response.text}") from e
        except Exception as e:
            raise ModelError(f"Ollama connection error: {e}") from e

    async def stream_completion(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncGenerator[str, AsyncGenerator]:
        """Stream completion from Ollama."""
        import httpx

        model = model or self.default_model
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()
                    async for chunk in resp.aiter_bytes():
                        if chunk:
                            text = chunk.decode("utf-8", errors="replace")
                            yield text
        except httpx.HTTPStatusError as e:
            raise ModelError(f"Stream failed: {e.response.status_code}") from e
        except Exception as e:
            raise ModelError(f"Stream error: {e}") from e

    async def generate_embedding(self, text: str, model: str | None = None) -> list[float]:
        """Generate embedding via Ollama."""
        import httpx

        model = model or "nomic-embed-text"
        url = f"{self.base_url}/api/embeddings"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json={"model": model, "prompt": text})
                resp.raise_for_status()
                return resp.json().get("embedding", [])
        except Exception as e:
            raise ModelError(f"Embedding generation failed: {e}") from e

    async def list_models(self) -> list[dict[str, Any]]:
        """List models available in Ollama."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                return data.get("models", [])
        except Exception:
            logger.warning("ollama_list_models_failed")
            return []


class OpenAICompatibleProvider(ModelProvider):
    """OpenAI-compatible API provider (LM Studio, vLLM, etc.)."""

    def __init__(self, base_url: str = "http://localhost:1234", default_model: str = "qwen2.5-coder:7b") -> None:
        super().__init__(base_url, default_model)

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Chat completion via OpenAI-compatible API."""
        import httpx

        model = model or self.default_model
        url = f"{self.base_url}/v1/chat/completions"

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            raise ModelError(f"API request failed: {e}") from e

    async def stream_completion(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream from OpenAI-compatible API."""
        import httpx

        model = model or self.default_model
        url = f"{self.base_url}/v1/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("POST", url, json=payload) as resp:
                    resp.raise_for_status()
                    async for chunk in resp.aiter_bytes():
                        if chunk:
                            yield chunk.decode("utf-8", errors="replace")
        except Exception as e:
            raise ModelError(f"Stream failed: {e}") from e

    async def generate_embedding(self, text: str, model: str | None = None) -> list[float]:
        """Generate embedding via OpenAI-compatible API."""
        import httpx

        url = f"{self.base_url}/v1/embeddings"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json={"model": model or "text-embedding-3-small", "input": text})
                resp.raise_for_status()
                result = resp.json()
                return result["data"][0]["embedding"]
        except Exception as e:
            raise ModelError(f"Embedding failed: {e}") from e

    async def list_models(self) -> list[dict[str, Any]]:
        """List available models."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/v1/models")
                resp.raise_for_status()
                data = resp.json()
                return data.get("data", [])
        except Exception:
            logger.warning("model_list_failed")
            return []


class ModelRouter:
    """Routes requests to the best available model provider with fallback."""

    def __init__(self) -> None:
        self._providers: dict[str, ModelProvider] = {}
        self._primary = "ollama"
        self._fallback = "openai_compat"

    def register_provider(self, name: str, provider: ModelProvider) -> None:
        self._providers[name] = provider

    async def get_provider(self, name: str | None = None) -> ModelProvider:
        """Get provider by name, or primary if not specified."""
        key = name or self._primary
        if key in self._providers:
            return self._providers[key]
        # Fallback to any available
        for p in self._providers.values():
            try:
                models = await p.list_models()
                if models:
                    logger.info("fallback_provider_selected", provider=p.__class__.__name__)
                    return p
            except Exception:
                continue
        raise ModelError("No available model providers")

    async def chat_completion(self, req: ChatCompletionRequest) -> dict[str, Any]:
        """Route chat completion to best provider."""
        provider = await self.get_provider(req.model)
        return await provider.chat_completion(
            messages=[m.model_dump() for m in req.messages],
            model=req.model,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            stream=req.stream,
            tools=req.tools,
        )

    async def stream_completion(self, req: ChatCompletionRequest) -> AsyncGenerator[str, None]:
        """Route streaming completion."""
        provider = await self.get_provider(req.model)
        async for chunk in provider.stream_completion(
            messages=[m.model_dump() for m in req.messages],
            model=req.model,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            tools=req.tools,
        ):
            yield chunk

    async def generate_embedding(self, req: EmbeddingRequest) -> EmbeddingResponse:
        """Route embedding generation."""
        provider = await self.get_provider(req.model)
        if isinstance(req.input, str):
            texts = [req.input]
        else:
            texts = req.input
        embeddings = []
        for text in texts:
            emb = await provider.generate_embedding(text, req.model)
            embeddings.append(emb)
        return EmbeddingResponse(model=req.model or "default", embeddings=embeddings, tokens=sum(len(t.split()) for t in texts))

    async def list_models(self) -> list[dict[str, Any]]:
        """List all models from all providers."""
        all_models: list[dict[str, Any]] = []
        for name, provider in self._providers.items():
            try:
                models = await provider.list_models()
                for m in models:
                    m["provider"] = name
                    all_models.append(m)
            except Exception:
                continue
        return all_models


# Global router singleton
def create_model_router(settings=None) -> ModelRouter:
    """Create and configure the model router with available providers."""
    if settings is None:
        from app.config.settings import get_settings
        settings = get_settings()

    router = ModelRouter()

    # Register Ollama
    try:
        ollama = OllamaProvider(
            base_url=settings.ollama_base_url,
            default_model=settings.ollama_default_model,
        )
        router.register_provider("ollama", ollama)
    except Exception as e:
        logger.warning("ollama_provider_init_failed", error=str(e))

    # Register OpenAI-compatible (LM Studio, etc.)
    try:
        openai_compat = OpenAICompatibleProvider()
        router.register_provider("openai_compat", openai_compat)
    except Exception as e:
        logger.warning("openai_compat_provider_init_failed", error=str(e))

    return router


model_router = create_model_router()