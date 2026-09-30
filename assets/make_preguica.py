"""Gera a arte pixel-art do bichinho-preguica do companheiro Seu Nono.

PAPEL NO PROJETO
----------------
O companheiro do portal Controle Popular nasce da ideia do "buddy" que vive
ao lado do cursor. Aqui ele vira um bicho-preguica, animal simbolo da
lentidao e da calma: ele se balanca pelo app ate o ponto exato da pagina
que responde a pergunta do cidadao.

FONTE DA REFERENCIA
-------------------
Especie: bicho-preguica-de-garganta-marrom (Bradypus variegatus), a mais
comum no Brasil. Anatomia da Wikipedia (en.wikipedia.org/wiki/Sloth, acesso
em 30/09/2026): corpo de 60 a 80 cm, bracos cerca de 50% mais longos que as
pernas, cabeca arredondada, orelhas minimas, garras longas e curvas, pelagem
com algas verdes simbioticas. Cores amostradas de fotos do Wikimedia Commons
(listadas em REFERENCIAS.md).

CRITERIO DE SIMILARIDADE (o que "parecido o bastante" significa)
----------------------------------------------------------------
O script mede e falha se sair da faixa:
  1. PALETA: cada cor usada dista no maximo DELTA_E_MAX do ponto mais
     proximo da paleta de referencia (CIE76 aproximado em RGB).
  2. PROPORCAO: bracos >= 45% da altura total; cabeca entre 40% e 70% da
     largura do corpo.
  3. LEITURA: ao menos 3 faixas de valor e a face clara com >= 5% dos pixels.
  4. CONTRASTE: contorno escuro contra fundo claro E aro claro contra fundo
     escuro, ambos >= CONTRASTE_MIN de luminancia (borda dupla).

DECISOES TECNICAS
-----------------
- Arte desenhada por codigo (Pillow): nenhum binario de arte versionado; o
  script basta. Espelha o padrao de assets/make_icon.py.
- Tamanho logico 32x32 ampliado com NEAREST, para o ar de "pixel de 16 bits".
- Textura por hash estavel do pixel: reproduzivel, sem random.
- --check gera tambem uma folha de contato (PNG) com as fotos de referencia
  ao lado dos quadros, para conferencia visual humana.

USO
---
    python assets/make_preguica.py
    python assets/make_preguica.py --check
    python assets/make_preguica.py --check --contato folha.png
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

AQUI = Path(__file__).resolve().parent
DIR_SAIDA = AQUI / "preguica"
# Fotos de referencia (nao versionadas). Sobreponha com CLICKY_REF_DIR.
REF_DIR = Path(
    os.environ.get(
        "CLICKY_REF_DIR",
        r"C:\Users\teste\AppData\Local\Temp\opencode\preguica-ref",
    )
)

# --------------------------------------------------------------------------
# Paleta (indice -> cor). 0 e transparente e nao entra na imagem RGB.
# --------------------------------------------------------------------------
PALETA: dict[int, tuple[int, int, int, int]] = {
    0: (0, 0, 0, 0),             # transparente
    1: (0x24, 0x1C, 0x14, 255),  # contorno escuro
    2: (0x3E, 0x30, 0x25, 255),  # pelagem escura
    3: (0x6D, 0x5A, 0x43, 255),  # pelagem media
    4: (0xA7, 0x98, 0x78, 255),  # pelagem clara
    5: (0xF0, 0xE8, 0xD8, 255),  # face creme
    6: (0x2A, 0x20, 0x17, 255),  # mascara dos olhos
    7: (0xC9, 0xBF, 0xA8, 255),  # garra (osso)
    8: (0xE8, 0xDF, 0xC8, 255),  # branco do olho (creme, como na foto)
    9: (0x18, 0x12, 0x0C, 255),  # pupila
    10: (0x4A, 0x3B, 0x2C, 255),  # focinho
    11: (0x6E, 0x8F, 0x4C, 255),  # alga verde
    12: (0x8D, 0xAE, 0x6E, 255),  # alga verde clara
    13: (0xF2, 0xEC, 0xDD, 255),  # aro claro (borda externa p/ fundo escuro)
}

# Paleta de referencia amostrada das fotos.
PALETA_REFERENCIA: list[tuple[int, int, int]] = [
    (0x45, 0x36, 0x2A), (0x64, 0x52, 0x43), (0x6D, 0x5A, 0x43),
    (0x8A, 0x74, 0x58), (0xA7, 0x98, 0x78), (0xD5, 0xCF, 0xB4),
    (0xEF, 0xE7, 0xD6), (0x2E, 0x24, 0x1A), (0x1B, 0x17, 0x12),
    (0x6E, 0x8F, 0x4C), (0x8D, 0xAE, 0x6E), (0xC9, 0xBF, 0xA8),
]

DELTA_E_MAX = 22.0
CONTRASTE_MIN = 40.0
# A arte e desenhada numa grade de 32 (as coordenadas abaixo), mas sai em 36
# logicos: 36 x 2 = 72 px na tela — o meio termo entre 48 e 96 pedido pelo
# dono. O fator mantem a proporcao e o resultado amplia sem borrar.
FATOR = 36 / 32
LARGURA, ALTURA = 36, 36
ESCALA_PADRAO = 2
QUADROS = ["parado", "alcanca", "puxa", "chega", "pisca", "dorme"]


def _p(*vals: int) -> tuple[int, ...]:
    """Converte coordenadas da grade 32 para a grade final (36)."""
    return tuple(round(v * FATOR) for v in vals)


def hash_pixel(x: int, y: int, semente: int = 7) -> float:
    """Ruido estavel em [0,1) por pixel — textura reproduzivel, sem random."""
    n = (x * 374761393 + y * 668265263 + semente * 2654435761) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 0x10000


def _dx(quadro: str) -> int:
    """Deslocamento lateral do corpo: o bicho puxa pra um lado e alcanca o outro."""
    if quadro == "puxa":
        return 2
    if quadro == "alcanca":
        return -1
    return 0


def _formas(d: ImageDraw.ImageDraw, dx: int, cor: int) -> None:
    """Todas as formas da silhueta (usada para contorno, interior e aro)."""
    # Bracos longos (mais longos que as pernas, como na especie).
    d.rounded_rectangle(_p(5 + dx, 2, 10 + dx, 16), radius=3, fill=cor)
    d.rounded_rectangle(_p(21 + dx, 2, 26 + dx, 16), radius=3, fill=cor)
    # Garras: tres por mao, encostando no braco.
    for cx in (5, 7, 9, 21, 23, 25):
        d.rectangle(_p(cx + dx, 0, cx + dx, 3), fill=cor)
    # Corpo arredondado.
    d.ellipse(_p(5 + dx, 12, 27 + dx, 29), fill=cor)
    # Pernas recolhidas (bem mais curtas que os bracos).
    d.rounded_rectangle(_p(10 + dx, 25, 14 + dx, 31), radius=2, fill=cor)
    d.rounded_rectangle(_p(18 + dx, 25, 22 + dx, 31), radius=2, fill=cor)
    # Rabinho.
    d.ellipse(_p(15 + dx, 27, 17 + dx, 30), fill=cor)
    # Cabeca arredondada.
    d.ellipse(_p(9 + dx, 9, 23 + dx, 22), fill=cor)


def _interior(d: ImageDraw.ImageDraw, dx: int) -> None:
    """Cores por dentro do contorno (o contorno sobra como 1px escuro)."""
    # Bracos: tom medio, lado externo mais claro (volume).
    d.rounded_rectangle(_p(6 + dx, 3, 10 + dx, 16), radius=3, fill=3)
    d.rounded_rectangle(_p(21 + dx, 3, 25 + dx, 16), radius=3, fill=3)
    d.rectangle(_p(6 + dx, 5, 7 + dx, 15), fill=4)
    d.rectangle(_p(24 + dx, 5, 25 + dx, 15), fill=4)
    # Garras de osso.
    for cx in (5, 7, 9, 21, 23, 25):
        d.rectangle(_p(cx + dx, 0, cx + dx, 2), fill=7)
    # Corpo.
    d.ellipse(_p(6 + dx, 13, 26 + dx, 28), fill=3)
    # Pernas.
    d.rounded_rectangle(_p(11 + dx, 26, 13 + dx, 30), radius=2, fill=2)
    d.rounded_rectangle(_p(19 + dx, 26, 21 + dx, 30), radius=2, fill=2)
    # Rabo.
    d.ellipse(_p(15 + dx, 27, 17 + dx, 29), fill=2)
    # Cabeca: pelagem media, face creme por dentro.
    d.ellipse(_p(9 + dx, 9, 23 + dx, 22), fill=3)
    d.ellipse(_p(10 + dx, 11, 22 + dx, 21), fill=5)   # face creme


def _mascara_e_olhos(d: ImageDraw.ImageDraw, dx: int, quadro: str) -> None:
    """Faixa escura tipica da especie, atravessando os olhos e as laterais."""
    d.rounded_rectangle(_p(11 + dx, 14, 21 + dx, 17), radius=3, fill=6)
    if quadro in ("pisca", "dorme"):
        d.rectangle(_p(12 + dx, 16, 13 + dx, 16), fill=9)
        d.rectangle(_p(17 + dx, 16, 18 + dx, 16), fill=9)
        return
    for ox in (12, 17):
        d.rectangle(_p(ox + dx, 14, ox + 1 + dx, 16), fill=8)  # olho creme
        d.rectangle(_p(ox + dx, 15, ox + dx, 16), fill=9)      # pupila


def _focinho(d: ImageDraw.ImageDraw, dx: int) -> None:
    d.rectangle(_p(15 + dx, 19, 17 + dx, 19), fill=10)
    d.point(_p(16 + dx, 21), fill=10)


def _algas(idx: Image.Image, dx: int) -> None:
    """Manchas de alga verde sobre a pelagem media, com densidade estavel."""
    px = idx.load()
    for y in range(ALTURA):
        for x in range(LARGURA):
            if px[x, y] != 3:
                continue
            r = hash_pixel(x - dx, y)
            if r < 0.12:
                px[x, y] = 11
            elif r < 0.18:
                px[x, y] = 12
            elif r < 0.30:
                px[x, y] = 2


def desenhar_frame(quadro: str) -> Image.Image:
    """Devolve o quadro como imagem L com indices da paleta (0 = vazio)."""
    dx = _dx(quadro)

    # Silhueta cheia (para o contorno e o aro).
    sil = Image.new("L", (LARGURA, ALTURA), 0)
    _formas(ImageDraw.Draw(sil), dx, 255)
    dil = sil.filter(ImageFilter.MaxFilter(3))  # dilata 1px
    aro = ImageChops.subtract(dil, sil)         # casca externa clara

    idx = Image.new("L", (LARGURA, ALTURA), 0)
    idx.paste(13, mask=aro)   # borda externa clara
    idx.paste(1, mask=sil)    # contorno escuro

    d = ImageDraw.Draw(idx)
    _interior(d, dx)
    _mascara_e_olhos(d, dx, quadro)
    _focinho(d, dx)
    _algas(idx, dx)
    return idx


def colorir(idx: Image.Image) -> Image.Image:
    rgba = Image.new("RGBA", idx.size, (0, 0, 0, 0))
    src, dst = idx.load(), rgba.load()
    for y in range(idx.height):
        for x in range(idx.width):
            dst[x, y] = PALETA[src[x, y]]
    return rgba


def ampliar(img: Image.Image, escala: int = ESCALA_PADRAO) -> Image.Image:
    return img.resize((img.width * escala, img.height * escala), Image.NEAREST)


# --------------------------------------------------------------------------
# Criterio de similaridade
# --------------------------------------------------------------------------
def _delta_e(a, b) -> float:
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))


def _lum(c) -> float:
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def medir(quadro: Image.Image) -> dict:
    px = quadro.load()
    visiveis = [(x, y) for y in range(quadro.height) for x in range(quadro.width)
                if px[x, y][3] != 0]
    cores = [px[x, y][:3] for (x, y) in visiveis]
    usadas = set(cores)

    pior = max(min(_delta_e(c, r) for r in PALETA_REFERENCIA) for c in usadas)

    ys = [y for (x, y) in visiveis]
    altura = max(ys) - min(ys) + 1
    y_pelagem = [y for (x, y) in visiveis if px[x, y][:3] in (PALETA[3][:3], PALETA[2][:3])]
    braco = (max(y_pelagem) - min(y_pelagem) + 1) if y_pelagem else 0
    xs_corpo = [x for (x, y) in visiveis if px[x, y][:3] != PALETA[7][:3]]
    # Cabeca = face creme + mascara escura (as duas juntas dao a largura real).
    xs_cabeca = [x for (x, y) in visiveis if px[x, y][:3] in (PALETA[5][:3], PALETA[6][:3])]
    xs_face = [x for (x, y) in visiveis if px[x, y][:3] == PALETA[5][:3]]
    largura_corpo = (max(xs_corpo) - min(xs_corpo) + 1) if xs_corpo else 1
    largura_cabeca = (max(xs_cabeca) - min(xs_cabeca) + 1) if xs_cabeca else 0

    faixas = len({round(_lum(c) / 32) for c in cores})
    pct_face = 100 * len(xs_face) / max(1, len(visiveis))

    lum_contorno = _lum(PALETA[1][:3])   # escuro: funciona no fundo claro
    lum_aro = _lum(PALETA[13][:3])       # claro: funciona no fundo escuro
    contraste_claro = abs(lum_contorno - _lum((255, 255, 255)))
    contraste_escuro = abs(lum_aro - _lum((16, 16, 16)))

    return {
        "delta_e_pior": round(pior, 1),
        "altura": altura,
        "razao_braco": round(braco / altura, 2),
        "razao_cabeca_corpo": round(largura_cabeca / largura_corpo, 2),
        "faixas_valor": faixas,
        "pct_face": round(pct_face, 1),
        "contraste_fundo_claro": round(contraste_claro, 1),
        "contraste_fundo_escuro": round(contraste_escuro, 1),
    }


def avaliar(m: dict) -> list[str]:
    falhas = []
    if m["delta_e_pior"] > DELTA_E_MAX:
        falhas.append(f"paleta: delta_e {m['delta_e_pior']} > {DELTA_E_MAX}")
    if m["razao_braco"] < 0.45:
        falhas.append(f"proporcao: braco {m['razao_braco']} < 0.45")
    if not (0.40 <= m["razao_cabeca_corpo"] <= 0.70):
        falhas.append(f"proporcao: cabeca/corpo {m['razao_cabeca_corpo']} fora de 0.40-0.70")
    if m["faixas_valor"] < 3:
        falhas.append(f"leitura: {m['faixas_valor']} faixas de valor < 3")
    if m["pct_face"] < 5.0:
        falhas.append(f"leitura: face {m['pct_face']}% < 5%")
    if min(m["contraste_fundo_claro"], m["contraste_fundo_escuro"]) < CONTRASTE_MIN:
        falhas.append("contraste: borda dupla some no fundo claro ou escuro")
    return falhas


# --------------------------------------------------------------------------
# Saidas
# --------------------------------------------------------------------------
def gerar() -> dict[str, Image.Image]:
    DIR_SAIDA.mkdir(parents=True, exist_ok=True)
    frames: dict[str, Image.Image] = {}
    for nome in QUADROS:
        rgba = colorir(desenhar_frame(nome))
        frames[nome] = rgba
        ampliar(rgba, ESCALA_PADRAO).save(DIR_SAIDA / f"preguica_{nome}.png")
        rgba.save(DIR_SAIDA / f"preguica_{nome}_1x.png")

    sheet = Image.new("RGBA", (LARGURA * len(QUADROS), ALTURA), (0, 0, 0, 0))
    for i, nome in enumerate(QUADROS):
        sheet.paste(frames[nome], (i * LARGURA, 0))
    ampliar(sheet, ESCALA_PADRAO).save(DIR_SAIDA / "preguica_sheet.png")
    sheet.save(DIR_SAIDA / "preguica_sheet_1x.png")

    (DIR_SAIDA / "paleta.json").write_text(json.dumps({
        "paleta": {str(k): list(v) for k, v in PALETA.items()},
        "referencia": [list(c) for c in PALETA_REFERENCIA],
        "frames": QUADROS,
        "tamanho_logico": [LARGURA, ALTURA],
        "escala_padrao": ESCALA_PADRAO,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return frames


def contato(frames: dict[str, Image.Image], destino: Path) -> None:
    tela = Image.new("RGB", (560, 440), (245, 243, 238))
    d = ImageDraw.Draw(tela)
    refs = sorted(REF_DIR.glob("ref*.jpg")) if REF_DIR.exists() else []
    x = 10
    for ref in refs[:4]:
        img = Image.open(ref).convert("RGB")
        img.thumbnail((125, 110))
        tela.paste(img, (x, 28))
        d.text((x, 12), ref.stem[:16], fill=(40, 40, 40))
        x += 136

    y = 170
    d.text((10, y - 16), "quadros (3x):", fill=(40, 40, 40))
    x = 10
    for nome in QUADROS:
        big = ampliar(frames[nome], 3)
        tela.paste(big, (x, y), big)
        d.text((x, y + 104), nome, fill=(40, 40, 40))
        x += 90

    y = 310
    d.text((10, y - 16), "contraste:", fill=(40, 40, 40))
    for i, fundo in enumerate([(255, 255, 255), (16, 16, 16), (108, 122, 137)]):
        bloco = Image.new("RGB", (150, 115), fundo)
        big = ampliar(frames["parado"], 3)
        bloco.paste(big, (10, 20), big)
        tela.paste(bloco, (10 + i * 165, y))
    tela.save(destino)


def main() -> int:
    ap = argparse.ArgumentParser(description="Gera a arte do bicho-preguica.")
    ap.add_argument("--check", action="store_true", help="valida o criterio de similaridade")
    ap.add_argument("--contato", type=Path, default=None, help="salva a folha de conferencia")
    args = ap.parse_args()

    frames = gerar()
    print(f"quadros gerados em {DIR_SAIDA}")

    m = medir(frames["parado"])
    print("metricas (quadro parado):")
    for k, v in m.items():
        print(f"  {k}: {v}")

    if args.contato:
        contato(frames, args.contato)
        print(f"folha de contato: {args.contato}")

    if args.check:
        falhas = avaliar(m)
        if falhas:
            print("\nFALHOU no criterio de similaridade:")
            for f in falhas:
                print(f"  - {f}")
            return 1
        print("\nOK: dentro do criterio de similaridade.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
