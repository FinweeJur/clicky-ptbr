"""
Carrega um mascote animado (padrao Petdex) e entrega os quadros por estado.

PAPEL NO PROJETO
----------------
O companheiro deixa de ter uma arte unica e passa a ter VARIOS mascotes,
animados. Um mascote e uma pasta com `spritesheet.png` (atlas de 192x208,
8 colunas x 9 linhas, 6 quadros por estado) e, opcionalmente, um `pet.json`.
A fonte e o Petdex (ver `mascotes/petdex.py`), o mesmo registro que o Hermes
Agent usa.

ESTADOS (linhas do atlas, de cima para baixo)
---------------------------------------------
idle, running-right, running-left, waving, jumping, failed, waiting,
running, review. Atlas antigo (8 linhas): idle, wave, run, failed, review,
jump, extra1, extra2.

DECISOES TECNICAS
-----------------
- A grade e deduzida do tamanho da imagem: `largura // 192`, `altura // 208`,
  aceitando o atlas novo (9 linhas) e o antigo (8 linhas).
- Escala unica (float) sobre os pixels nativos; padrao 0.35 (~67 px de largura)
  para o bicho nao tomar a tela.
- Animacao por tempo: `quadro_em(estado, segundos)` fecha o ciclo no
  `loop_ms` do atlas (1100 ms). Sem `random`: o quadro e funcao do tempo.
- PyQt6 QPixmap: a mesma engine do overlay; nenhuma dependencia nova.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from mascotes import petdex

ESTADO_PADRAO = "idle"


class Mascote:
    """Um mascote carregado do disco, pronto para desenhar."""

    def __init__(self, dir_mascote: Path, escala: float = 0.35) -> None:
        self.dir = Path(dir_mascote)
        self.escala = float(escala)
        self.disponivel = False
        self.rotulo = self.dir.name
        self._colunas = 0
        self._linhas = 0
        self._linhas_nomes: list[str] = []
        self._quadros: dict[str, list[QPixmap]] = {}
        self._loop_ms = petdex.LOOP_MS
        self._carregar()

    # ── carga ────────────────────────────────────────────────────────────
    def _carregar(self) -> None:
        folha_caminho = self.dir / "spritesheet.png"
        if not folha_caminho.exists():
            return
        folha = QPixmap(str(folha_caminho))
        if folha.isNull():
            return

        # Tamanho da celula: do pet.json, se houver; senao, o padrao Petdex.
        cw, ch = petdex.FRAME_W, petdex.FRAME_H
        self.rotulo = self.dir.name
        import json
        pj = self.dir / "pet.json"
        if pj.exists():
            try:
                dados = json.loads(pj.read_text(encoding="utf-8"))
                cw = int(dados.get("cellW", cw))
                ch = int(dados.get("cellH", ch))
                self._loop_ms = int(dados.get("loopMs", self._loop_ms))
                if dados.get("displayName"):
                    self.rotulo = str(dados["displayName"])
            except Exception:
                pass
        if (self.dir / "fonte.json").exists():
            try:
                import json as _j
                self.rotulo = _j.loads((self.dir / "fonte.json").read_text(encoding="utf-8")).get("displayName", self.rotulo)
            except Exception:
                pass

        self._colunas = max(1, folha.width() // cw)
        self._linhas = max(1, folha.height() // ch)
        self._linhas_nomes = petdex.LINHAS_NOVO if self._linhas >= 9 else petdex.LINHAS_ANTIGO
        self._linhas_nomes = self._linhas_nomes[: self._linhas]

        largura = max(1, round(cw * self.escala))
        altura = max(1, round(ch * self.escala))
        for r, nome in enumerate(self._linhas_nomes):
            quadros: list[QPixmap] = []
            for c in range(min(self._colunas, petdex.FRAMES_POR_ESTADO)):
                recorte = folha.copy(c * cw, r * ch, cw, ch)
                quadros.append(recorte.scaled(
                    largura, altura,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))
            self._quadros[nome] = quadros
        self.disponivel = bool(self._quadros)

    # ── consulta ─────────────────────────────────────────────────────────
    @property
    def estado_padrao(self) -> str:
        return ESTADO_PADRAO if ESTADO_PADRAO in self._quadros else next(iter(self._quadros), "")

    def tem_estado(self, estado: str) -> bool:
        return estado in self._quadros and bool(self._quadros[estado])

    def resumo_estados(self) -> list[str]:
        return list(self._quadros.keys())

    def quadro_em(self, estado: str, segundos: float) -> QPixmap | None:
        """Quadro do estado no instante `segundos` (ciclo fecha no loop do atlas)."""
        nomes = [estado, self.estado_padrao, "wave", "run"]
        quadros = next((self._quadros[n] for n in nomes if n in self._quadros), None)
        if not quadros:
            return None
        n = len(quadros)
        fracao = (segundos * 1000.0) % max(1, self._loop_ms) / max(1, self._loop_ms)
        return quadros[min(n - 1, int(fracao * n))]


def carregar_ativo(cfg) -> Mascote | None:
    """Carrega o mascote ativo da config, se estiver instalado."""
    slug = getattr(cfg, "mascote_slug", "") or ""
    escala = getattr(cfg, "mascote_escala", 0.35)
    if not slug:
        instalados = petdex.listar_instalados()
        if not instalados:
            return None
        slug = instalados[0]
    dirp = petdex.dir_do_mascote(slug)
    if not (dirp / "spritesheet.png").exists():
        return None
    mascote = Mascote(dirp, escala=escala)
    return mascote if mascote.disponivel else None
