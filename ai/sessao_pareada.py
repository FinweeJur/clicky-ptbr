"""
Cliente da sessao pareada do portal — parear, ouvir (SSE) e perguntar.

PAPEL NO PROJETO
----------------
O portal Controle Popular cria uma sessao curta e mostra um codigo no widget
do site. O companheiro de desktop entra UMA vez com esse codigo (`parear`),
passa a ouvir os turnos (`ouvir`, por SSE) e pode disparar o turno
(`perguntar`). No turno, o portal devolve a `RespostaCompanheiro` com a fala e
os "galhos" (pontos de apoio) — o gerenciador fala a resposta e caminha o
bichinho ate os alvos que a ponte local mapeou.

FONTE OFICIAL / CONTRATO
------------------------
O contrato esta no portal, em `apps/web/lib/companheiro/` (contrato, sessao,
responder). As rotas: `/api/companheiro/sessao`, `.../parear`,
`.../[id]/eventos` (SSE) e `.../[id]/perguntar`.

DECISAO TECNICA
---------------
`httpx` (ja e dependencia do app) para as chamadas e para o stream SSE. A
leitura do SSE fica num acumulador puro (`AcumuladorSSE`), testavel sem rede.
`COMPANHEIRO_TOKEN` opcional: quando o portal exige, vai no header
`Authorization: Bearer`.
"""

from __future__ import annotations

import json
from typing import AsyncIterator, Callable, Iterable, Iterator, Optional, Union

import httpx


def _headers(token: Optional[str]) -> dict[str, str]:
    cabecalhos = {"Content-Type": "application/json"}
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    return cabecalhos


class AcumuladorSSE:
    """Monta um evento a partir das linhas cruas do SSE.

    O protocolo separa eventos por linha em branco; `data:` carrega o JSON e
    `event:` nomeia o tipo. Linhas comecando em `:` sao comentarios (o `: ping`
    que mantem a conexao viva) e sao ignoradas.
    """

    def __init__(self) -> None:
        self.evento: Optional[str] = None
        self.dados: list[str] = []

    def linha(self, linha: str) -> Optional[dict]:
        """Processa uma linha; devolve o evento quando a moldura fecha."""
        if linha == "":
            return self._fechar()
        if linha.startswith(":"):
            return None  # comentario / ping
        if linha.startswith("event:"):
            self.evento = linha[len("event:"):].strip()
        elif linha.startswith("data:"):
            self.dados.append(linha[len("data:"):].lstrip())
        # `retry:` e `id:` nao interessam aqui.
        return None

    def _fechar(self) -> Optional[dict]:
        if not self.dados:
            self.evento = None
            return None
        texto = "\n".join(self.dados)
        self.dados = []
        evento = self.evento
        self.evento = None
        try:
            carga = json.loads(texto)
        except Exception:
            return {"tipo": evento, "bruto": texto}
        if isinstance(carga, dict):
            if evento and "tipo" not in carga:
                carga["tipo"] = evento
            return carga
        return {"tipo": evento, "dados": carga}


def parsear_evento_sse(linhas: Iterable[str]) -> Iterator[dict]:
    """Versao sincrona do parser, para teste e para fluxo sem httpx."""
    acumulador = AcumuladorSSE()
    for linha in linhas:
        evento = acumulador.linha(linha)
        if evento is not None:
            yield evento
    final = acumulador._fechar()  # moldura sem linha em branco no fim
    if final is not None:
        yield final


async def _iterar_eventos(resposta: httpx.Response) -> AsyncIterator[dict]:
    """Le o corpo SSE assincrono e emite os eventos parseados."""
    acumulador = AcumuladorSSE()
    async for linha in resposta.aiter_lines():
        evento = acumulador.linha(linha)
        if evento is not None:
            yield evento
    final = acumulador._fechar()
    if final is not None:
        yield final


async def parear(
    base: str,
    codigo: str,
    token: Optional[str] = None,
    cliente: Optional[httpx.AsyncClient] = None,
) -> dict:
    """Pareia a sessao pelo codigo. Devolve {"id", "expiraEm"}."""
    base = base.rstrip("/")
    async with _cliente(cliente) as cli:
        resp = await cli.post(
            f"{base}/api/companheiro/sessao/parear",
            json={"codigo": codigo},
            headers=_headers(token),
        )
        if resp.status_code == 404:
            raise RuntimeError("Codigo invalido, ja usado ou expirado.")
        resp.raise_for_status()
        return resp.json()


async def perguntar(
    base: str,
    sessao_id: str,
    pergunta: str,
    token: Optional[str] = None,
    pathname: Optional[str] = None,
    titulo: Optional[str] = None,
    cliente: Optional[httpx.AsyncClient] = None,
) -> dict:
    """Dispara UM turno na sessao. Devolve a `RespostaCompanheiro`."""
    base = base.rstrip("/")
    corpo = {"pergunta": pergunta}
    if pathname:
        corpo["pathname"] = pathname
    if titulo:
        corpo["titulo"] = titulo
    async with _cliente(cliente) as cli:
        resp = await cli.post(
            f"{base}/api/companheiro/sessao/{sessao_id}/perguntar",
            json=corpo,
            headers=_headers(token),
            timeout=90.0,
        )
        resp.raise_for_status()
        return resp.json()


async def ouvir(
    base: str,
    sessao_id: str,
    ao_evento: Callable[[dict], None],
    token: Optional[str] = None,
    cliente: Optional[httpx.AsyncClient] = None,
) -> None:
    """Ouve o SSE da sessao e chama `ao_evento` a cada quadro.

    Bloqueia ate a conexao cair ou o chamador cancelar a task. `read=None`
    desliga o timeout de leitura: o stream fica aberto entre turnos.
    """
    base = base.rstrip("/")
    timeout = httpx.Timeout(connect=10.0, read=None, write=10.0, pool=10.0)
    async with _cliente(cliente, timeout) as cli:
        async with cli.stream(
            "GET",
            f"{base}/api/companheiro/sessao/{sessao_id}/eventos",
            headers=_headers(token),
        ) as resp:
            resp.raise_for_status()
            async for evento in _iterar_eventos(resp):
                ao_evento(evento)


class _cliente:
    """Contexto que usa o cliente injetado ou cria/descarta um proprio."""

    def __init__(
        self, cliente: Optional[httpx.AsyncClient], timeout: Union[float, httpx.Timeout] = 30.0
    ) -> None:
        self._cliente = cliente
        self._timeout = timeout
        self._proprio: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> httpx.AsyncClient:
        if self._cliente is not None:
            return self._cliente
        self._proprio = httpx.AsyncClient(timeout=self._timeout)
        return self._proprio

    async def __aexit__(self, *args) -> None:
        if self._proprio is not None:
            await self._proprio.aclose()
            self._proprio = None
