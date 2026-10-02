"""
Petdex — galeria e instalador de mascotes animados do companheiro.

PAPEL NO PROJETO
----------------
O companheiro do Controle Popular sai de uma arte unica e passa a aceitar
VARIOS mascotes animados. A fonte e o Petdex (petdex.dev), o mesmo registro
publico que o Hermes Agent (NousResearch) usa: spritesheets de 192x208,
8 colunas x 9 linhas, 6 quadros por estado.

FONTE OFICIAL
-------------
- Manifesto: https://petdex.dev/api/manifest (JSON, sem autenticacao).
- Formato do atlas: 8 colunas x 9 linhas de 192x208 (padrao petdex/Codex).
- Estados (linhas, de cima para baixo): idle, running-right, running-left,
  waving, jumping, failed, waiting, running, review.

DECISOES TECNICAS
-----------------
- Sem dependencia externa: urllib da biblioteca padrao baixa manifesto e arte.
- Os mascotes baixados ficam em `mascotes/instalados/<slug>/` (fora do git).
- O `pet.json` de cada mascote carrega o essencial; a grade e deduzida do
  tamanho da imagem, aceitando tanto o atlas novo (9 linhas) quanto o antigo
  (8 linhas).

USO
---
    from mascotes import petdex
    petdex.instalar("lulu-capybara-2")
    petdex.listar_instalados()
"""
from __future__ import annotations

import json
import os
import shutil
import urllib.request
from pathlib import Path

MANIFEST_URL = "https://petdex.dev/api/manifest"
UA = "controle-popular-companion/0.1 (mascotes; +https://controlepopular.com.br)"

AQUI = Path(__file__).resolve().parent
DIR_INSTALADOS = AQUI / "instalados"

# Geometria do atlas petdex (pixels).
FRAME_W = 192
FRAME_H = 208
FRAMES_POR_ESTADO = 6
LOOP_MS = 1100

# Ordem das linhas no atlas novo (9 linhas) e no antigo (8 linhas).
LINHAS_NOVO = ["idle", "running-right", "running-left", "waving", "jumping",
               "failed", "waiting", "running", "review"]
LINHAS_ANTIGO = ["idle", "wave", "run", "failed", "review", "jump", "extra1", "extra2"]


def _baixar(url: str, destino: Path, timeout: float = 30.0) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r, open(destino, "wb") as f:
        shutil.copyfileobj(r, f)


def buscar_manifesto(timeout: float = 20.0) -> list[dict]:
    """Baixa a lista publica de mascotes do Petdex (sem autenticacao)."""
    req = urllib.request.Request(MANIFEST_URL, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        dados = json.loads(r.read().decode("utf-8"))
    pets = dados.get("pets") if isinstance(dados, dict) else None
    return [p for p in (pets or []) if p.get("slug") and p.get("spritesheetUrl")]


def procurar(termo: str, limite: int = 20) -> list[dict]:
    """Filtra o manifesto por substring no slug ou no nome."""
    t = (termo or "").strip().lower()
    if not t:
        return []
    achados = []
    for p in buscar_manifesto():
        if t in str(p.get("slug", "")).lower() or t in str(p.get("displayName", "")).lower():
            achados.append(p)
        if len(achados) >= limite:
            break
    return achados


def listar_instalados() -> list[str]:
    """Slugs dos mascotes ja baixados."""
    if not DIR_INSTALADOS.exists():
        return []
    return sorted(p.name for p in DIR_INSTALADOS.iterdir() if (p / "spritesheet.png").exists())


def dir_do_mascote(slug: str) -> Path:
    return DIR_INSTALADOS / slug


def instalar(slug: str, forcar: bool = False) -> Path:
    """Baixa um mascote do Petdex para `mascotes/instalados/<slug>/`.

    Devolve o diretorio do mascote. Se ja existir e `forcar` for False,
    devolve o que ja esta instalado (sem baixar de novo).
    """
    destino = dir_do_mascote(slug)
    if (destino / "spritesheet.png").exists() and not forcar:
        return destino

    entrada = next((p for p in buscar_manifesto() if p.get("slug") == slug), None)
    if entrada is None:
        raise RuntimeError(f"Mascote '{slug}' nao esta no Petdex.")

    destino.mkdir(parents=True, exist_ok=True)
    _baixar(entrada["spritesheetUrl"], destino / "spritesheet.png")
    if entrada.get("petJsonUrl"):
        try:
            _baixar(entrada["petJsonUrl"], destino / "pet.json")
        except Exception:
            pass  # o pet.json e opcional; a grade sai do tamanho da imagem
    (destino / "fonte.json").write_text(
        json.dumps({
            "slug": slug,
            "displayName": entrada.get("displayName", slug),
            "kind": entrada.get("kind", "pet"),
            "submittedBy": entrada.get("submittedBy", ""),
            "spritesheetUrl": entrada.get("spritesheetUrl", ""),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return destino


def remover(slug: str) -> bool:
    """Apaga um mascote instalado. False se ele nao estava instalado."""
    destino = dir_do_mascote(slug)
    if not destino.exists():
        return False
    shutil.rmtree(destino)
    return True
