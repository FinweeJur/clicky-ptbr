"""
Provedor do portal Controle Popular: o companheiro pergunta ao Seu Nono.

PAPEL NO PROJETO
----------------
Quando ligado, o companheiro deixa de falar direto com um modelo e passa a
falar com o cerebro do portal: `POST /api/companheiro`. O portal cuida da
escada determinista e do RAG do Seu Nono, e devolve a resposta com fontes
("galhos") e a fala curta. Assim o cidadao recebe a MESMA resposta que o
site daria — sem duplicar regra nem acervo.

FONTE OFICIAL
-------------
O portal e o proprio Controle Popular (controlepopular.com.br). O contrato
esta em `lib/companheiro/contrato.ts` no repositorio do portal.

DECISOES TECNICAS
-----------------
- A foto da tela NUNCA vai ao portal: so a pergunta (texto) e enviada. O
  contrato recusa imagem de proposito. O contexto de tela fica no app.
- `COMPANHEIRO_TOKEN` opcional: quando o portal exige, o app manda no header
  `Authorization: Bearer`. Sem token, a rota e publica (so limite por IP).
- Sem internet ou portal fora do ar: levanta erro claro; o gerenciador troca
  para o provedor local.
- httpx, sem SDK, no mesmo estilo dos outros provedores.
"""
from __future__ import annotations

from typing import AsyncIterator, List

import httpx

from ai.base_provider import BaseLLMProvider, Message
from config import cfg


class PortalProvider(BaseLLMProvider):
    """Fala com o endpoint /api/companheiro do portal Controle Popular."""

    def __init__(self) -> None:
        self.rotulo = "Seu Nono (portal)"
        self._base = cfg.portal_url.rstrip("/")
        headers = {"Content-Type": "application/json"}
        if cfg.companheiro_token:
            headers["Authorization"] = f"Bearer {cfg.companheiro_token}"
        self._client = httpx.AsyncClient(timeout=90.0, headers=headers)

    async def close(self) -> None:
        """Fecha o cliente HTTP quando o provedor e trocado."""
        await self._client.aclose()

    async def stream_response(
        self,
        user_text: str,
        screenshots_b64: List[str],
        history: List[Message],
        system_prompt: str,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """Manda a pergunta ao portal e devolve a resposta citada.

        `screenshots_b64` e `system_prompt` sao ignorados de proposito: o
        portal tem o proprio acervo e as proprias regras editoriais. A imagem
        nao sai da maquina.
        """
        payload = {"pergunta": user_text}
        try:
            resp = await self._client.post(
                f"{self._base}/api/companheiro", json=payload
            )
        except httpx.ConnectError as e:
            raise RuntimeError(
                f"Nao alcancei o portal em {self._base}. Confira a conexao."
            ) from e

        if resp.status_code == 401:
            raise RuntimeError(
                "O portal recusou a chamada (401). Confira COMPANHEIRO_TOKEN."
            )
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Portal respondeu HTTP {resp.status_code}: {resp.text[:200]}"
            )

        dados = resp.json()
        if dados.get("erro"):
            raise RuntimeError(f"Portal: {dados['erro']}")

        # A resposta completa, com marcadores [n], e o que o painel mostra.
        # (A fala curta do contrato sera usada pelo TTS numa fase seguinte.)
        texto = str(dados.get("resposta") or "").strip()
        if not texto:
            raise RuntimeError("Portal respondeu sem resposta.")
        yield texto

    async def health_check(self) -> bool:
        try:
            r = await self._client.get(f"{self._base}/api/companheiro")
            # Sem GET definido o portal devolve 405, mas isso ja prova que
            # o servidor esta de pe.
            return r.status_code < 500
        except Exception:
            return False
