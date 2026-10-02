"""Gera a ONCA-PINTADA cartoon no formato de mascote (9 estados x 6 quadros).

PAPEL NO PROJETO
----------------
A onca-pintada e o grande felino do Brasil e nao existe no Petdex (medido:
0 resultados para jaguar/onca/leopardo/jaguatirica). Este gerador cria a arte
NOSSA, no mesmo formato dos mascotes (linhas = estados, 6 quadros por linha),
para a onca virar mascote local do companheiro.

DESENHO
-------
Lobo (vista lateral, virada para a direita) dourado com rosaceas, barriga
creme, patas e focinho escuros. Formas por codigo (Pillow) sobre uma grade de
48x36, com contorno escuro automatico. Movimento por operacoes de pixel.

SAIDA
-----
`mascotes/instalados/onca/` com `spritesheet.png` (576x648) e `pet.json`.

DECISOES TECNICAS
-----------------
- Paleta enxuta (dourado + sombra + creme + escuro + branco do olho).
- Celula 96x72 = grade 48x36 ampliada 2x (NEAREST), sem borrar.
- Animacao deterministica (quadro = funcao do indice), sem random.

USO
---
    python assets/make_onca_petdex.py
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

SAIDA = Path(__file__).resolve().parent.parent / "mascotes" / "instalados" / "onca"

W, H = 48, 36
CEL_W, CEL_H = 96, 72
FATOR = 2
COLS, LINHAS = 6, 9
LOOP_MS = 1100

ESTADOS = ["idle", "running-right", "running-left", "waving", "jumping",
           "failed", "waiting", "running", "review"]

# Paleta (indice -> RGBA). 0 = transparente.
PALETA: dict[int, tuple[int, int, int, int]] = {
    0: (0, 0, 0, 0),
    1: (0x24, 0x12, 0x09, 255),  # contorno / nariz / patas
    2: (0xE0, 0xA2, 0x3C, 255),  # pelo dourado
    3: (0xC0, 0x7E, 0x22, 255),  # sombra do pelo
    4: (0x4A, 0x2E, 0x15, 255),  # contorno da rosacea
    5: (0xF2, 0xE4, 0xC4, 255),  # barriga / peito claro
    6: (0xFB, 0xF3, 0xDF, 255),  # focinho claro
    7: (0xFF, 0xFF, 0xFF, 255),  # branco do olho
    8: (0x14, 0x0A, 0x05, 255),  # pupila
}

ESQ = {1, 8}  # indices escuros (para detector de olho fechado)


def _grade_base() -> list[list[int]]:
    """Desenha a onca na grade 48x36 e devolve os indices da paleta."""
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)

    # Cauda (atras, a esquerda) — grossa e caida.
    d.line([(6, 18), (3, 22), (2, 27)], fill=2, width=3)
    d.line([(2, 27), (3, 30)], fill=1, width=3)

    # Pernas (traseiras e dianteiras).
    for x0, x1 in ((9, 13), (16, 20), (25, 29), (31, 35)):
        d.rectangle((x0, 24, x1, 33), fill=2)
        d.rectangle((x0, 31, x1, 33), fill=1)   # pata escura

    # Corpo (elipse) e barriga clara.
    d.ellipse((5, 12, 36, 30), fill=2)
    d.ellipse((9, 21, 30, 30), fill=5)

    # Cabeca, orelhas e focinho.
    d.polygon([(32, 11), (33, 4), (38, 10)], fill=2)
    d.polygon([(41, 10), (45, 4), (47, 12)], fill=2)
    d.polygon([(33, 10), (34, 6), (37, 10)], fill=4)
    d.polygon([(42, 10), (44, 6), (46, 11)], fill=4)
    d.ellipse((29, 7, 47, 25), fill=2)
    d.ellipse((38, 15, 47, 23), fill=6)          # focinho
    d.rectangle((44, 16, 46, 19), fill=1)        # nariz

    # Olhos (maiores, com brilho).
    for ox in (33, 40):
        d.rectangle((ox, 12, ox + 2, 15), fill=7)
        d.rectangle((ox + 1, 13, ox + 1, 14), fill=8)

    # Rosaceas (aneis escuros com centro dourado) espalhadas no corpo.
    for (cx, cy) in ((11, 16), (17, 15), (24, 16), (13, 22), (21, 23), (28, 21), (31, 17)):
        d.ellipse((cx - 2, cy - 2, cx + 1, cy + 1), outline=4, fill=2)

    g = [[0] * W for _ in range(H)]
    px = img.load()
    for y in range(H):
        for x in range(W):
            g[y][x] = px[x, y]

    # Contorno escuro automatico: pixel do bicho vizinho do fundo.
    contorno = [linha[:] for linha in g]
    for y in range(H):
        for x in range(W):
            if g[y][x] == 0:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < W and 0 <= ny < H) or g[ny][nx] == 0:
                    contorno[y][x] = 1
                    break
    return contorno


def _deslocar_faixa(g, y0, dx):
    """Desloca uma faixa de linhas para o lado (pernas/rabo)."""
    saida = [linha[:] for linha in g]
    for y in range(y0, len(g)):
        saida[y] = [0] * W
        for x in range(W):
            nx = x + dx
            if 0 <= nx < W:
                saida[y][nx] = g[y][x]
    return saida


def _descer(g, dy):
    saida = [[0] * W for _ in range(H)]
    for y in range(H):
        ny = y + dy
        if 0 <= ny < H:
            saida[ny] = g[y][:]
    return saida


def _espelhar(g):
    return [linha[::-1] for linha in g]


def _fechar_olhos(g):
    """Troca o branco/pupila por pelo (olhos fechados) e poe um traco escuro."""
    saida = [linha[:] for linha in g]
    for y in range(H):
        for x in range(W):
            if g[y][x] in ESQ or g[y][x] == 7:
                vizinho_pelo = any(
                    0 <= x + dx < W and 0 <= y + dy < H and g[y + dy][x + dx] == 2
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                )
                if vizinho_pelo:
                    saida[y][x] = 2
    return saida


# (dx_pernas, dy_corpo, olhos_fechados) por quadro.
ROTEIROS: dict[str, list[tuple[int, int, bool]]] = {
    "idle":           [(0, 0, False), (0, 0, False), (0, -1, False), (0, 0, True), (0, 0, False), (0, 0, False)],
    "running-right":  [(0, 0, False), (1, 0, False), (0, 0, False), (1, 0, False), (0, 0, False), (1, 0, False)],
    "running-left":   [(0, 0, False), (-1, 0, False), (0, 0, False), (-1, 0, False), (0, 0, False), (-1, 0, False)],
    "waving":         [(0, 0, False), (0, -1, False), (0, -2, False), (0, -1, False), (0, 0, False), (0, 0, False)],
    "jumping":        [(0, 0, False), (0, -2, False), (0, -3, False), (0, -2, False), (0, 0, False), (0, 0, False)],
    "failed":         [(0, 1, True), (0, 1, True), (0, 1, True), (0, 0, True), (0, 1, True), (0, 1, True)],
    "waiting":        [(0, 0, False), (0, 0, False), (0, -1, False), (0, -1, False), (0, 0, True), (0, 0, False)],
    "running":        [(0, 0, False), (1, 0, False), (0, 0, False), (1, 0, False), (0, 0, False), (1, 0, False)],
    "review":         [(0, 0, False), (0, -1, False), (0, 0, False), (0, -1, False), (0, 0, False), (0, 0, False)],
}


def _frame(estado: str, i: int):
    dxp, dy, fechar = ROTEIROS[estado][i]
    g = _grade_base()
    if dxp:
        g = _deslocar_faixa(g, 24, dxp)   # pernas se movem
    if dy:
        g = _descer(g, dy)
    if fechar:
        g = _fechar_olhos(g)
    if estado == "running-left":
        g = _espelhar(g)
    return g


def gerar() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    atlas = Image.new("RGBA", (CEL_W * COLS, CEL_H * LINHAS), (0, 0, 0, 0))
    for r, estado in enumerate(ESTADOS):
        for c in range(COLS):
            g = _frame(estado, c)
            off_x = (CEL_W - W * FATOR) // 2
            off_y = (CEL_H - H * FATOR) // 2
            px = atlas.load()
            for y in range(H):
                for x in range(W):
                    idx = g[y][x]
                    if idx == 0:
                        continue
                    cor = PALETA[idx]
                    for oy in range(FATOR):
                        for ox in range(FATOR):
                            px[c * CEL_W + off_x + x * FATOR + ox,
                               r * CEL_H + off_y + y * FATOR + oy] = cor
    atlas.save(SAIDA / "spritesheet.png")
    (SAIDA / "pet.json").write_text(json.dumps({
        "id": "onca",
        "displayName": "Onca-pintada",
        "cellW": CEL_W,
        "cellH": CEL_H,
        "rows": ESTADOS,
        "framesPerState": COLS,
        "loopMs": LOOP_MS,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (SAIDA / "fonte.json").write_text(json.dumps({
        "slug": "onca",
        "displayName": "Onca-pintada",
        "kind": "local",
        "submittedBy": "Controle Popular",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"onca: {atlas.size} -> {SAIDA}")


if __name__ == "__main__":
    gerar()
