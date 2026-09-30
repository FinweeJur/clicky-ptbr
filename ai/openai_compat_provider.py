"""
Provedor generico para qualquer endpoint compativel com a API da OpenAI.

PAPEL NO PROJETO
----------------
Da vida aos botoes simplificados do companheiro Seu Nono: o DeepSeek e o
Sabia da Maritaca. Os dois falam o mesmo dialeto da OpenAI (`POST
/chat/completions`), entao um unico provedor serve aos dois — e tambem a
qualquer outro servidor compativel que o usuario queira plugar.

FONTE OFICIAL
-------------
- OpenAI: formato de /chat/completions (platform.openai.com/docs).
- DeepSeek: https://api-docs.deepseek.com (compativel com a API da OpenAI).
- Maritaca/Sabia: https://docs.maritaca.ai — a propria documentacao diz que e
  compativel com a biblioteca da OpenAI; basta trocar a base_url para
  https://chat.maritaca.ai/api e usar um modelo da familia Sabia.

DECISOES TECNICAS
-----------------
- httpx em vez do SDK `openai`, para nao arrastar dependencia e seguir o mesmo
  estilo do ai/lmstudio_provider.py (streaming por linha "data:").
- Imagem e OPCIONAL (`aceita_imagem`). Os modelos de chat do DeepSeek e o
  Sabiazinho respondem por texto: sem visao, o screenshot e descartado em
  silencio e a resposta sai sem contexto de tela — o app avisa na interface.
  Isso evita mandar um bloco de imagem que o provedor recusaria com erro.
- Nenhuma chave e guardada aqui; ela vem da config (`AI_API_KEY_DEEPSEEK`,
  `AI_API_KEY_MARITACA`) e nunca aparece em log.
"""
from __future__ import annotations

import json
from typing import AsyncIterator, List

import httpx

from ai.base_provider import BaseLLMProvider, Message


class OpenAICompatProvider(BaseLLMProvider):
    """Provedor para endpoints compativeis com /chat/completions da OpenAI.

    Parametros (mesmos nomes usados pelos presets em `config`):
        base_url: raiz da API, sem barra final (ex.: https://api.deepseek.com/v1).
        api_key: chave do provedor (Bearer).
        modelo: id do modelo a usar por padrao.
        aceita_imagem: True se o modelo aceita imagem no contexto.
        rotulo: nome amigavel para a interface (ex.: "DeepSeek").
        timeout: segundos de espera por resposta (modelos lentos pedem mais).
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        modelo: str,
        aceita_imagem: bool = False,
        rotulo: str = "Compativel com OpenAI",
        timeout: float = 120.0,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._modelo = modelo
        self._aceita_imagem = aceita_imagem
        self.rotulo = rotulo
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            limits=httpx.Limits(max_keepalive_connections=4, max_connections=8),
        )

    async def close(self) -> None:
        """Fecha o cliente HTTP — chamado quando o provedor e trocado."""
        await self._client.aclose()

    async def stream_response(
        self,
        user_text: str,
        screenshots_b64: List[str],
        history: List[Message],
        system_prompt: str,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        escolhido = model or self._modelo

        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})

        # Monta o turno do usuario. Com visao, blocos multimodais no padrao
        # OpenAI; sem visao, so o texto (a imagem e ignorada de proposito).
        if self._aceita_imagem and screenshots_b64:
            conteudo: list = []
            for img_b64 in screenshots_b64:
                conteudo.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                })
            conteudo.append({"type": "text", "text": user_text})
            messages.append({"role": "user", "content": conteudo})
        else:
            messages.append({"role": "user", "content": user_text})

        payload = {
            "model": escolhido,
            "messages": messages,
            "max_tokens": 1024,
            "stream": True,
        }

        try:
            async with self._client.stream(
                "POST", f"{self._base}/chat/completions", json=payload
            ) as resp:
                if resp.status_code >= 400:
                    corpo = (await resp.aread()).decode("utf-8", "ignore")[:300]
                    raise RuntimeError(
                        f"{self.rotulo} respondeu HTTP {resp.status_code}: {corpo}"
                    )
                async for linha in resp.aiter_lines():
                    if not linha.strip() or not linha.startswith("data:"):
                        continue
                    dado = linha[len("data:"):].strip()
                    if dado == "[DONE]":
                        break
                    try:
                        obj = json.loads(dado)
                        delta = obj["choices"][0]["delta"].get("content")
                        if delta:
                            yield delta
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
        except httpx.ConnectError as e:
            raise RuntimeError(
                f"Nao consegui alcancar {self.rotulo} em {self._base}. "
                "Confira a conexao e a chave."
            ) from e

    async def health_check(self) -> bool:
        """True se o servidor responde. Um 404 em /models ainda conta como
        alcancavel — nem todo provedor expoe a lista de modelos."""
        try:
            r = await self._client.get(f"{self._base}/models", timeout=8)
            return r.status_code < 500
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        """Ids de modelo reportados por /models (vazio quando nao ha endpoint)."""
        try:
            r = await self._client.get(f"{self._base}/models", timeout=8)
            dados = r.json()
            return [m["id"] for m in dados.get("data", [])]
        except Exception:
            return []
