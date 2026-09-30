"""
Carrega a arte do bicho-preguica e calcula o balanco do movimento.

PAPEL NO PROJETO
----------------
O companheiro do portal Controle Popular usa um bicho-preguica no lugar do
triangulo azul original do Clicky. Este modulo entrega os quadros prontos
(QPixmap) e a matematica do movimento: o balanco pendular e a troca de
quadro "braco a braco" enquanto ele atravessa a tela.

A arte vem de `assets/make_preguica.py` -> `assets/preguica/preguica_sheet_1x.png`
(uma tira de quadros 32x32). Ver `assets/preguica/REFERENCIAS.md`.

DECISOES TECNICAS
-----------------
- Sem arte binaria escrita a mao: o quadro e lido da tira gerada por script.
- Ampliacao com FastTransformation (vizinho mais proximo), para nao borrar os
  pixels — e o que preserva o ar de "pixel de 16 bits".
- Nenhuma dependencia alem do PyQt6, que o app ja usa.

USO
---
    bicho = Preguica(escala=1)
    bicho.quadro("puxa")           # QPixmap do quadro
    bicho.quadro_em_voo(0.4)       # quadro certo para 40% do trajeto
    bicho.inclinacao(0.4, voando=True)   # graus de balanco
"""
from __future__ import annotations

import math
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

DIR_ARTE = Path(__file__).resolve().parent.parent / "assets" / "preguica"
TIRA = DIR_ARTE / "preguica_sheet_1x.png"
QUADROS = ["parado", "alcanca", "puxa", "chega", "pisca", "dorme"]
# Grade logica da arte. Com escala 2 o bicho sai em 72 px — o "meio termo"
# entre 48 e 96 pedido pelo dono.
TAMANHO_LOGICO = 36


class Preguica:
    """A arte e o movimento do bicho. Degrada em silencio se a arte faltar."""

    def __init__(self, escala: int = 1) -> None:
        self._escala = max(1, int(escala))
        self._disponivel = False
        self._quadros: dict[str, QPixmap] = {}
        self._carregar()

    def _carregar(self) -> None:
        if not TIRA.exists():
            return
        tira = QPixmap(str(TIRA))
        if tira.isNull():
            return
        for i, nome in enumerate(QUADROS):
            recorte = tira.copy(i * TAMANHO_LOGICO, 0, TAMANHO_LOGICO, TAMANHO_LOGICO)
            if self._escala != 1:
                recorte = recorte.scaled(
                    TAMANHO_LOGICO * self._escala,
                    TAMANHO_LOGICO * self._escala,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation,
                )
            self._quadros[nome] = recorte
        self._disponivel = bool(self._quadros)

    @property
    def disponivel(self) -> bool:
        """True quando a arte foi encontrada e carregada."""
        return self._disponivel

    @property
    def tamanho(self) -> int:
        return TAMANHO_LOGICO * self._escala

    def quadro(self, nome: str) -> QPixmap | None:
        return self._quadros.get(nome)

    def quadro_em_voo(self, u: float) -> QPixmap | None:
        """Quadro do trajeto em funcao do progresso u em [0,1].

        O bicho "puxa" e "alcanca" alternadamente — o gesto de galgar um galho
        de cada vez. O ritmo e lento de proposito: e uma preguica.
        """
        if u <= 0.05 or u >= 0.95:
            return self._quadros.get("parado")
        passo = int(u * 6) % 2
        return self._quadros.get("puxa" if passo else "alcanca")

    def quadro_parado(self, t: float) -> QPixmap | None:
        """Quadro em repouso: pisca de vez em quando."""
        ciclo = t % 3.2
        if 2.8 <= ciclo < 3.0:
            return self._quadros.get("pisca")
        return self._quadros.get("parado")

    def inclinacao(self, u: float, voando: bool = False) -> float:
        """Angulo do balanco, em graus.

        Em voo, um pendulo de 5 balancos completos ao longo do trajeto, com
        amplitude de 12 graus. Parado, uma oscilacao lenta de 4 graus.
        """
        if voando:
            return 12.0 * math.sin(u * math.pi * 2 * 2.5)
        return 4.0 * math.sin(u * math.pi * 2)
