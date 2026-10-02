"""Gera a arte pixel-art cartoon do bichinho-preguica (companheiro Seu Nono).

PAPEL NO PROJETO
----------------
O companheiro do portal Controle Popular usa um bicho-preguica no lugar do
triangulo azul do Clicky. A primeira versao era realista (baseada em foto). O
dono pediu o estilo CARTOON da referencia do Pinterest, com alta semelhanca e
movimento. Esta versao entrega esse estilo.

FONTE DA REFERENCIA
-------------------
Imagem cartoon enviada pelo dono (Pinterest), arquivada fora do repositorio em
`CLICKY_REF_DIR`. A forma foi tracada em grade de 36 e esta EMBUTIDA abaixo
(`BASE`), entao a arte sai sem depender da imagem. Ver REFERENCIAS.md.

⚠️ A forma deriva da referencia. Antes de uso comercial, trocar por desenho
proprio — a atribuicao esta em REFERENCIAS.md.

CRITERIO DE SIMILARIDADE (meta: 95%)
------------------------------------
Com a referencia presente, o script mede:
  - IoU da silhueta (nossa x referencia);
  - similaridade de cor (1 - erro medio de cor).
E exige COMPOSTO = 0.5*IoU + 0.5*cor >= 0.95.

MOVIMENTO (movimento dos pixels)
--------------------------------
Os quadros saem do mesmo desenho por operacoes de pixel, para o bicho se
balancar e alcancar os locais: o corpo desliza para os lados (`alcanca`,
`puxa`), o bicho desce (`chega`) e dorme (`dorme`). O overlay do app soma a
isso o voo em arco.

DECISOES TECNICAS
-----------------
- Grade logica 36x29 embutida, emoldiurada para 36x36 (o loader do app le
  36x36). Ampliacao com NEAREST: nao borra os pixels.
- Sem dependencia alem do Pillow. Deterministico.

USO
---
    python assets/make_preguica.py
    python assets/make_preguica.py --check
    CLICKY_REF_DIR=<pasta> python assets/make_preguica.py --check --contato folha.png
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

from PIL import Image, ImageDraw

AQUI = Path(__file__).resolve().parent
DIR_SAIDA = AQUI / "preguica"
REF_DIR = Path(os.environ.get("CLICKY_REF_DIR", r"C:\Users\teste\AppData\Local\Temp\opencode\preguica-ref"))

LARGURA, ALTURA = 36, 36      # quadro logico (o loader do app le 36x36)
GRID_LARG, GRID_ALT = 36, 29  # desenho tracado da referencia
ESCALA_PREVIA = 4
LIMITE_CORPO = 8              # a partir desta linha comeca o corpo (acima e galho/bracos)

# Paleta cartoon (indice -> RGBA). 0 = transparente. Tons amostrados da propria
# referencia (12 cores), o que sustenta a meta de 95% de similaridade.
PALETA: dict[int, tuple[int, int, int, int]] = {
    0: (0, 0, 0, 0),
    1: (237, 212, 170, 255),  # #EDD4AA pelo claro / face
    2: (219, 167, 115, 255),  # #DBA773
    3: (215, 163, 113, 255),  # #D7A371
    4: (215, 162, 112, 255),  # #D7A270 corpo
    5: (132, 197, 116, 255),  # #84C574 folha
    6: (211, 156, 110, 255),  # #D39C6E
    7: (181, 120, 90, 255),   # #B5785A sombra
    8: (145, 82, 73, 255),    # #915249
    9: (124, 58, 60, 255),    # #7C3A3C
    10: (121, 20, 45, 255),   # #79142D
    11: (90, 14, 43, 255),    # #5A0E2B
    12: (48, 10, 28, 255),    # #300A1C
    13: (51, 0, 23, 255),     # #330017
    14: (0, 0, 57, 255),      # #000039
    15: (0, 0, 0, 255),       # #000000
}

FACE = 1                      # indice do pelo claro / face
ESCUROS = {8, 9, 10, 11, 12, 13, 14, 15}

# Desenho tracado da referencia (36x29), indices da paleta acima (hex 0-b).
BASE: list[str] = [
    "0000000000000000000000000098b0090000",
    "0000000000000000000000000988b8770000",
    "0000000000000000000000000879b7590000",
    "0000000bb0abb000b00bbb0008abba900000",
    "0bbb0b9479789909689779b00bbabbb00000",
    "babab92237769bb6277769bbaabbbbb00000",
    "bbabb6228a99bd82469b9bbbbabb00000000",
    "bbbb92628ddbab72629bbbbbd000089a0000",
    "000072628a99ab72628878b0008872648000",
    "000b62628877a07262787790962111126800",
    "000b62628877a0724279778a611111112490",
    "000866428877b07664288787222111111270",
    "00082642787790746327979688711111117b",
    "000824342987808224428987898111671170",
    "00082664279778b634426996633b61877628",
    "000826624278779826442692111811997769",
    "000b66444427988863446289117613787670",
    "000b66444442688a6244442861137111627b",
    "000b72444444222663444442421111112280",
    "000082444444444234444444466211266490",
    "0000b6244444444444444444433666442700",
    "000007244444444444444444444333326900",
    "00000b726334444444444444444436728000",
    "000000862664444444444444443334680000",
    "000000084462433444444444436666700000",
    "000000008466466432344243346279000000",
    "000000000986264266644634626890000000",
    "00000000000987763632267789a000000000",
    "000000000000000988888890000000000000",
]

QUADROS = ["parado", "alcanca", "puxa", "chega", "pisca", "dorme"]


def _grade_base() -> list[list[int]]:
    return [[int(c, 16) for c in linha] for linha in BASE]


def _deslocar_corpo(g: list[list[int]], dx: int) -> list[list[int]]:
    """Desliza as linhas do corpo (abaixo do galho) — o balanco do bicho."""
    saida = [linha[:] for linha in g]
    for y in range(LIMITE_CORPO, len(g)):
        saida[y] = [0] * GRID_LARG
        for x in range(GRID_LARG):
            novo = x + dx
            if 0 <= novo < GRID_LARG:
                saida[y][novo] = g[y][x]
    return saida


def _descer(g: list[list[int]], dy: int) -> list[list[int]]:
    """Empurra o desenho inteiro para baixo (o bicho pende mais)."""
    saida = [[0] * GRID_LARG for _ in range(len(g))]
    for y in range(len(g)):
        ny = y + dy
        if 0 <= ny < len(g):
            saida[ny] = g[y][:]
    return saida


def _piscar(g: list[list[int]]) -> list[list[int]]:
    """Fecha os olhos: apaga os pixels escuros cercados de pelo claro (face)."""
    saida = [linha[:] for linha in g]
    for y in range(len(g)):
        for x in range(GRID_LARG):
            if g[y][x] not in ESCUROS:
                continue
            vizinhos = 0
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < GRID_LARG and 0 <= ny < len(g) and g[ny][nx] == FACE:
                    vizinhos += 1
            if vizinhos >= 2:
                saida[y][x] = FACE
    return saida


def montar_quadro(nome: str) -> list[list[int]]:
    g = _grade_base()
    if nome == "alcanca":
        g = _deslocar_corpo(g, 1)
    elif nome == "puxa":
        g = _deslocar_corpo(g, -1)
    elif nome == "chega":
        g = _descer(g, 1)
    elif nome == "dorme":
        g = _descer(_piscar(g), 1)
    return g


def colorir(g: list[list[int]]) -> Image.Image:
    img = Image.new("RGBA", (LARGURA, ALTURA), (0, 0, 0, 0))
    for y in range(len(g)):
        for x in range(GRID_LARG):
            if g[y][x]:
                img.putpixel((x, y), PALETA[g[y][x]])
    return img


def ampliar(img: Image.Image, escala: int = ESCALA_PREVIA) -> Image.Image:
    return img.resize((img.width * escala, img.height * escala), Image.NEAREST)


# --------------------------------------------------------------------------
# Similaridade com a referencia
# --------------------------------------------------------------------------
def _carregar_referencia() -> tuple[list[list[tuple[int, int, int, int]]], list[list[bool]]] | None:
    alvo = None
    if REF_DIR.exists():
        for nome in ("ref_brave.jpg",):
            p = REF_DIR / nome
            if p.exists():
                alvo = p
                break
        if alvo is None:
            cands = sorted(REF_DIR.glob("ref*.jpg"))
            alvo = cands[0] if cands else None
    if alvo is None:
        return None

    im = Image.open(alvo).convert("RGBA")
    px = im.load()
    L, A = im.size
    minx, miny, maxx, maxy = L, A, -1, -1
    for y in range(A):
        for x in range(L):
            r, g, b, _ = px[x, y]
            if min(r, g, b) > 232 and (max(r, g, b) - min(r, g, b)) < 16:
                px[x, y] = (0, 0, 0, 0)
            else:
                minx = min(minx, x); miny = min(miny, y)
                maxx = max(maxx, x); maxy = max(maxy, y)
    bicho = im.crop((minx, miny, maxx + 1, maxy + 1)).resize((GRID_LARG, GRID_ALT), Image.LANCZOS)
    rgb = bicho.convert("RGB").load()
    alfa = bicho.getchannel("A").load()
    pal = [[rgba for rgba in [(*rgb[x, y], alfa[x, y]) for x in range(GRID_LARG)]] for y in range(GRID_ALT)]
    mask = [[alfa[x, y] >= 110 for x in range(GRID_LARG)] for y in range(GRID_ALT)]
    return pal, mask


def medir(g: list[list[int]]) -> dict:
    vis = [(x, y) for y in range(len(g)) for x in range(GRID_LARG) if g[y][x]]
    ref = _carregar_referencia()

    metrica = {"iou_silhueta": None, "sim_cor": None, "composto": None}
    if ref is None:
        return metrica
    pal, mask = ref

    inter = uniao = 0
    for y in range(GRID_ALT):
        for x in range(GRID_LARG):
            nosso = g[y][x] != 0
            deles = mask[y][x]
            if nosso or deles:
                uniao += 1
            if nosso and deles:
                inter += 1
    iou = inter / uniao if uniao else 0.0

    dist_total = 0.0
    MAX_REDMEAN = 806.0  # normalizador da distancia redmean (max teorico)
    for y in range(GRID_ALT):
        for x in range(GRID_LARG):
            nosso = g[y][x] != 0
            deles = mask[y][x]
            if not nosso and not deles:
                continue
            if nosso != deles:
                dist_total += MAX_REDMEAN   # silhueta divergiu neste ponto
                continue
            pr, pg, pb, _ = PALETA[g[y][x]]
            r, gg, b, _ = pal[y][x]
            # Distancia redmean: aproxima a percepcao humana melhor que o RGB cru.
            dr, dg, db = pr - r, pg - gg, pb - b
            rbar = (pr + r) / 2
            dist_total += math.sqrt(
                (2 + rbar / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rbar) / 256) * db * db
            )
    pontos = sum(1 for y in range(GRID_ALT) for x in range(GRID_LARG)
                 if g[y][x] != 0 or mask[y][x])
    dist_medio = dist_total / pontos if pontos else MAX_REDMEAN
    sim_cor = 1.0 - dist_medio / MAX_REDMEAN

    metrica.update({
        "iou_silhueta": round(iou, 3),
        "sim_cor": round(sim_cor, 3),
        "composto": round(0.5 * iou + 0.5 * sim_cor, 3),
    })
    return metrica


def avaliar(m: dict) -> list[str]:
    if m.get("composto") is None:
        return []  # sem referencia, nada a exigir
    return [] if m["composto"] >= 0.95 else [f"similaridade {m['composto']} < 0.95"]


# --------------------------------------------------------------------------
# Saida
# --------------------------------------------------------------------------
def gerar() -> dict[str, Image.Image]:
    DIR_SAIDA.mkdir(parents=True, exist_ok=True)
    frames: dict[str, Image.Image] = {}
    for nome in QUADROS:
        img = colorir(montar_quadro(nome))
        frames[nome] = img
        ampliar(img).save(DIR_SAIDA / f"preguica_{nome}.png")
        img.save(DIR_SAIDA / f"preguica_{nome}_1x.png")

    sheet = Image.new("RGBA", (LARGURA * len(QUADROS), ALTURA), (0, 0, 0, 0))
    for i, nome in enumerate(QUADROS):
        sheet.paste(frames[nome], (i * LARGURA, 0))
    ampliar(sheet).save(DIR_SAIDA / "preguica_sheet.png")
    sheet.save(DIR_SAIDA / "preguica_sheet_1x.png")

    (DIR_SAIDA / "paleta.json").write_text(json.dumps({
        "paleta": {str(k): list(v) for k, v in PALETA.items()},
        "frames": QUADROS,
        "tamanho_logico": [LARGURA, ALTURA],
        "grade_desenho": [GRID_LARG, GRID_ALT],
        "escala_previa": ESCALA_PREVIA,
        "estilo": "cartoon",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return frames


def contato(frames: dict[str, Image.Image], destino: Path) -> None:
    preferida = REF_DIR / "ref_brave.jpg"
    if preferida.exists():
        refs = [preferida]
    else:
        refs = sorted(REF_DIR.glob("ref*.jpg")) if REF_DIR.exists() else []
    largura = 40 + max(1, len(refs[:1])) * 260 + len(QUADROS) * 130
    tela = Image.new("RGB", (largura, 360), (245, 243, 238))
    d = ImageDraw.Draw(tela)
    x = 20
    for ref in refs[:1]:
        im = Image.open(ref).convert("RGB")
        im.thumbnail((240, 300))
        tela.paste(im, (x, 40))
        d.text((x, 20), "REFERENCIA", fill=(40, 40, 40))
        x += 260
    for nome in QUADROS:
        big = ampliar(frames[nome], 3)
        tela.paste(big, (x, 60), big)
        d.text((x, 40), nome, fill=(40, 40, 40))
        x += 130
    tela.save(destino)


def main() -> int:
    ap = argparse.ArgumentParser(description="Gera a arte do bicho-preguica (cartoon).")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--contato", type=Path, default=None)
    args = ap.parse_args()

    frames = gerar()
    print(f"quadros gerados em {DIR_SAIDA}")

    m = medir(montar_quadro("parado"))
    if m.get("composto") is None:
        print("metrica: sem referencia em CLICKY_REF_DIR (check pulado)")
    else:
        print("metricas (vs referencia):")
        for k, v in m.items():
            print(f"  {k}: {v}")

    if args.contato:
        contato(frames, args.contato)
        print(f"folha de contato: {args.contato}")

    if args.check:
        falhas = avaliar(m)
        if falhas:
            print("\nFALHOU:")
            for f in falhas:
                print(f"  - {f}")
            return 1
        print("\nOK: similaridade >= 0.95" if m.get("composto") is not None else "\nOK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
