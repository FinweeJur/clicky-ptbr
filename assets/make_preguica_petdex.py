"""Gera a preguica ANIMADA no formato de mascote (9 estados x 6 quadros).

PAPEL NO PROJETO
----------------
A preguica e o mascote do projeto, mas no sistema de mascotes ela precisa do
mesmo formato do Petdex: um atlas com linhas = estados e 6 quadros por linha.
Aqui a arte cartoon (grade 36x29, de `make_preguica.py`) vira movimento por
operacoes de pixel: balanco, passarinhos de passo, pulo, olhos fechados.

SAIDA
-----
`mascotes/instalados/preguica/` com `spritesheet.png` (6 colunas x 9 linhas de
72x64) e `pet.json`. E um mascote local (arte nossa), nao baixado do Petdex.

DECISOES TECNICAS
-----------------
- Reusa a grade e a paleta de `assets/make_preguica.py` (um so desenho base).
- Celula 72x64 = grade 36x29 ampliada 2x (NEAREST), centrada. Sem borrar.
- Animacao deterministica: quadro e funcao do indice, sem random.

USO
---
    python assets/make_preguica_petdex.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_preguica import (  # noqa: E402
    BASE, PALETA, GRID_LARG, GRID_ALT, _deslocar_corpo, _descer, _piscar,
)

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
SAIDA = RAIZ / "mascotes" / "instalados" / "preguica"

CEL_W, CEL_H = 72, 64
FATOR = 2  # grade 36x29 -> 72x58
COLS, LINHAS = 6, 9
LOOP_MS = 1100

# Nomes das linhas, na ordem do Petdex.
ESTADOS = ["idle", "running-right", "running-left", "waving", "jumping",
           "failed", "waiting", "running", "review"]


def _grade_base() -> list[list[int]]:
    return [[int(c, 16) for c in linha] for linha in BASE]


def _aplicar(g, dx=0, dy=0, pisca=False, y0=0):
    if dx:
        g = _deslocar_corpo(g, dx)
    if dy:
        g = _descer(g, dy)
    if pisca:
        g = _piscar(g)
    return g


# Cada estado: 6 quadros como (dx, dy, pisca).
ROTEIROS: dict[str, list[tuple[int, int, bool]]] = {
    "idle":           [(0, 0, False), (1, 0, False), (1, 0, False), (0, 0, True), (-1, 0, False), (0, 0, False)],
    "running-right":  [(0, 0, False), (1, 0, False), (2, 0, False), (1, 0, False), (2, 0, False), (1, 0, False)],
    "running-left":   [(0, 0, False), (-1, 0, False), (-2, 0, False), (-1, 0, False), (-2, 0, False), (-1, 0, False)],
    "waving":         [(0, 0, False), (0, -1, False), (0, -2, False), (0, -1, False), (0, 0, False), (0, 0, False)],
    "jumping":        [(0, 0, False), (0, -2, False), (0, -3, False), (0, -2, False), (0, 0, False), (0, 0, False)],
    "failed":         [(0, 1, True), (0, 1, True), (0, 1, True), (0, 0, True), (0, 1, True), (0, 1, True)],
    "waiting":        [(0, 0, False), (0, 0, False), (1, 0, False), (1, 0, False), (0, 0, True), (0, 0, False)],
    "running":        [(0, 0, False), (1, 0, False), (0, 0, False), (1, 0, False), (0, 0, False), (1, 0, False)],
    "review":         [(0, 0, False), (0, -1, False), (0, 0, False), (0, -1, False), (0, 0, False), (0, 0, False)],
}


def _colorir(g) -> list[list[tuple[int, int, int, int]]]:
    """Grade de indices -> grade de RGBA (com a paleta da preguica)."""
    return [[PALETA[g[y][x]] if g[y][x] else (0, 0, 0, 0) for x in range(GRID_LARG)]
            for y in range(GRID_ALT)]


def _frame_rgba(estado: str, i: int) -> list[list[tuple[int, int, int, int]]]:
    dx, dy, pisca = ROTEIROS[estado][i]
    return _colorir(_aplicar(_grade_base(), dx=dx, dy=dy, pisca=pisca))


def gerar() -> None:
    from PIL import Image, ImageDraw

    SAIDA.mkdir(parents=True, exist_ok=True)
    atlas = Image.new("RGBA", (CEL_W * COLS, CEL_H * LINHAS), (0, 0, 0, 0))
    desenho = ImageDraw.Draw(atlas)
    for r, estado in enumerate(ESTADOS):
        for c in range(COLS):
            grade = _frame_rgba(estado, c)
            # Desenha a grade ampliada 2x, centrada na celula.
            off_x = (CEL_W - GRID_LARG * FATOR) // 2
            off_y = (CEL_H - GRID_ALT * FATOR) // 2
            for y in range(GRID_ALT):
                for x in range(GRID_LARG):
                    px = grade[y][x]
                    if px[3] == 0:
                        continue
                    cor = (px[0], px[1], px[2], 255)
                    desenho.rectangle(
                        [c * CEL_W + off_x + x * FATOR, r * CEL_H + off_y + y * FATOR,
                         c * CEL_W + off_x + (x + 1) * FATOR - 1,
                         r * CEL_H + off_y + (y + 1) * FATOR - 1],
                        fill=cor,
                    )
    atlas.save(SAIDA / "spritesheet.png")
    (SAIDA / "pet.json").write_text(json.dumps({
        "id": "preguica",
        "displayName": "Preguica",
        "cellW": CEL_W,
        "cellH": CEL_H,
        "rows": ESTADOS,
        "framesPerState": COLS,
        "loopMs": LOOP_MS,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (SAIDA / "fonte.json").write_text(json.dumps({
        "slug": "preguica",
        "displayName": "Preguica",
        "kind": "local",
        "submittedBy": "Controle Popular",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"preguica animada: {atlas.size} -> {SAIDA}")


if __name__ == "__main__":
    gerar()
