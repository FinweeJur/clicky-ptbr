"""
Geometria e CORS da ponte local — a parte pura, testavel sem rede nem Qt.

PAPEL NO PROJETO
----------------
O portal Controle Popular manda, pelo navegador, as coordenadas dos alvos do
Seu Nono (chips de citacao [n] e o botao "Abrir pagina"). O companheiro de
desktop recebe esse pacote num servidor local em 127.0.0.1 e precisa
transformar a coordenada do viewport em coordenada de TELA, para o
bicho-preguica caminhar ate o alvo certo.

FORMATO DO PACOTE (contrato do portal, `apps/web/lib/companheiro/ponte.ts`)
--------------------------------------------------------------------------
    {
      "sessaoId": "...",             # opcional
      "url": "https://www.controlepopular.com.br/betla",
      "origem": {"x": 120, "y": 90},  # canto do viewport em px de tela
      "viewport": {"largura": 1280, "altura": 720, "dpr": 1.5},
      "alvos": [
        {"tipo": "fonte", "indice": 1,
         "retangulo": {"x": 40, "y": 300, "largura": 18, "altura": 16},
         "visivel": true},
        {"tipo": "abrir-pagina",
         "retangulo": {"x": 40, "y": 340, "largura": 120, "altura": 28},
         "visivel": true}
      ],
      "em": 1727650000000
    }

DECISAO TECNICA
---------------
Nada aqui importa `aiohttp`, `httpx` ou PyQt: sao funcoes puras, para rodar no
`unittest` do venv sem subir servidor nem tela.
"""

from __future__ import annotations

from typing import Optional

# Origens que o navegador pode usar para chamar a ponte. O portal publico e os
# dois enderecos de desenvolvimento local. A pagina so alcanca 127.0.0.1 com o
# preflight de Private Network Access respondido — por isso a lista e fechada.
ORIGENS_PADRAO = (
    "https://www.controlepopular.com.br",
    "https://controlepopular.com.br",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def origem_permitida(origem: Optional[str], permitidas=ORIGENS_PADRAO) -> Optional[str]:
    """Devolve a origem se ela estiver na lista; senao, None.

    Nao usar `*` com credenciais nem refletir origem desconhecida: o servidor
    escuta no loopback e so a pagina do portal precisa falar com ele.
    """
    if not origem:
        return None
    origem = origem.strip().rstrip("/")
    for permitida in permitidas:
        if origem == permitida.strip().rstrip("/"):
            return origem
    return None


def cabecalhos_cors(origem: Optional[str], permitidas=ORIGENS_PADRAO) -> dict[str, str]:
    """Cabecalhos de CORS + Private Network Access para a resposta.

    `Access-Control-Allow-Private-Network: true` e o que o Chrome atual exige
    para deixar uma pagina PUBLICA (https) chamar `http://127.0.0.1`. Sem ele,
    o preflight falha e o navegador bloqueia a ponte em silencio.
    """
    base = {
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Max-Age": "600",
        "Vary": "Origin",
    }
    permitida = origem_permitida(origem, permitidas)
    if permitida:
        base["Access-Control-Allow-Origin"] = permitida
        base["Access-Control-Allow-Private-Network"] = "true"
    return base


def _centro(retangulo: dict) -> tuple[float, float]:
    x = float(retangulo.get("x", 0))
    y = float(retangulo.get("y", 0))
    largura = float(retangulo.get("largura", 0))
    altura = float(retangulo.get("altura", 0))
    return x + largura / 2.0, y + altura / 2.0


def coordenadas_do_alvo(pacote: Optional[dict], indice: int) -> Optional[tuple[float, float]]:
    """Coordenada de TELA do centro do chip de citacao `indice`.

    Soma a origem do viewport ao centro do retangulo. Devolve None quando o
    pacote nao existe, o alvo nao esta visivel ou nao ha chip com esse indice.
    """
    if not pacote:
        return None
    origem = pacote.get("origem") or {}
    ox = float(origem.get("x", 0))
    oy = float(origem.get("y", 0))
    for alvo in pacote.get("alvos") or []:
        if alvo.get("tipo") != "fonte":
            continue
        if int(alvo.get("indice", -1)) != int(indice):
            continue
        if not alvo.get("visivel", True):
            return None
        cx, cy = _centro(alvo.get("retangulo") or {})
        return ox + cx, oy + cy
    return None


def coordenadas_do_botao_abrir(pacote: Optional[dict]) -> Optional[tuple[float, float]]:
    """Coordenada de TELA do botao "Abrir pagina", quando presente e visivel."""
    if not pacote:
        return None
    origem = pacote.get("origem") or {}
    ox = float(origem.get("x", 0))
    oy = float(origem.get("y", 0))
    for alvo in pacote.get("alvos") or []:
        if alvo.get("tipo") != "abrir-pagina":
            continue
        if not alvo.get("visivel", True):
            return None
        cx, cy = _centro(alvo.get("retangulo") or {})
        return ox + cx, oy + cy
    return None
