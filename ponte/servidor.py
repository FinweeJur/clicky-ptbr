"""
Servidor local da ponte — recebe, do navegador, os alvos do Seu Nono.

PAPEL NO PROJETO
----------------
O companheiro de desktop e o "olho" que caminha ate o alvo. O portal (o
"cerebro") manda as coordenadas dos chips de citacao [n] e do botao "Abrir
pagina" para `http://127.0.0.1:<porta>/ponte`. Este servidor:
  1. responde ao preflight de Private Network Access (o Chrome exige para uma
     pagina publica chamar o loopback);
  2. guarda o ULTIMO pacote em `self.ultimo`, que o gerenciador le para saber
     onde estao os galhos.

DECISAO TECNICA
---------------
`http.server` da biblioteca padrao, em thread daemon. Sem `aiohttp` nem
`flask`: o venv do app nao tem servidor web instalado e nao vale somar uma
dependencia por causa de uma rota. Escuta SO em 127.0.0.1 — nunca `0.0.0.0`.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Optional

from ponte.geometria import (
    ORIGENS_PADRAO,
    cabecalhos_cors,
    coordenadas_do_alvo,
    coordenadas_do_botao_abrir,
)


class PonteLocal:
    """Servidor HTTP no loopback que recebe os alvos do Seu Nono.

    `ao_pacote` e chamado a cada POST valido (opcional). O pacote cru fica
    sempre em `self.ultimo`.
    """

    def __init__(
        self,
        ao_pacote: Optional[Callable[[dict], None]] = None,
        porta: int = 8765,
        origens_permitidas=ORIGENS_PADRAO,
    ) -> None:
        self.porta = int(porta)
        self._ao_pacote = ao_pacote
        self.origens_permitidas = tuple(origens_permitidas)
        self.ultimo: Optional[dict] = None
        self._servidor: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def iniciar(self) -> None:
        """Sobe o servidor numa thread daemon. Idempotente."""
        if self._servidor is not None:
            return
        handler = _criar_handler(self)
        self._servidor = ThreadingHTTPServer(("127.0.0.1", self.porta), handler)
        self._servidor.daemon_threads = True
        self._thread = threading.Thread(
            target=self._servidor.serve_forever, name="ponte-local", daemon=True
        )
        self._thread.start()

    def parar(self) -> None:
        """Derruba o servidor. Chamar de OUTRA thread (a que serve nao pode)."""
        servidor = self._servidor
        self._servidor = None
        self._thread = None
        if servidor is not None:
            servidor.shutdown()
            servidor.server_close()

    def coordenadas_do_indice(self, indice: int) -> Optional[tuple[float, float]]:
        """Coordenada de tela do chip de citacao `indice`, no ultimo pacote."""
        return coordenadas_do_alvo(self.ultimo, indice)

    def coordenadas_do_botao(self) -> Optional[tuple[float, float]]:
        """Coordenada de tela do botao "Abrir pagina", no ultimo pacote."""
        return coordenadas_do_botao_abrir(self.ultimo)


def _criar_handler(ponte: PonteLocal):
    """Cria a classe do handler fechada sobre a instancia (compartilha estado)."""

    class _Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _responder(self, status: int, corpo: bytes = b"") -> None:
            cors = cabecalhos_cors(self.headers.get("Origin"), ponte.origens_permitidas)
            self.send_response(status)
            for chave, valor in cors.items():
                self.send_header(chave, valor)
            if corpo:
                self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            if corpo:
                self.wfile.write(corpo)

        def do_OPTIONS(self):  # noqa: N802 (nome exigido pelo http.server)
            # Preflight: CORS + Private Network Access.
            self._responder(204)

        def do_GET(self):  # noqa: N802
            # Sem GET util; 405 ja prova que o servidor esta de pe.
            self._responder(405, b'{"erro":"use POST"}')

        def do_POST(self):  # noqa: N802
            if self.path.split("?")[0] != "/ponte":
                self._responder(404, b'{"erro":"rota desconhecida"}')
                return
            try:
                tamanho = int(self.headers.get("Content-Length", 0) or 0)
            except ValueError:
                tamanho = 0
            bruto = self.rfile.read(tamanho) if tamanho > 0 else b""
            try:
                pacote = json.loads(bruto.decode("utf-8") or "{}")
            except Exception:
                self._responder(400, b'{"erro":"json invalido"}')
                return
            if not isinstance(pacote, dict):
                self._responder(400, b'{"erro":"json invalido"}')
                return

            ponte.ultimo = pacote
            if ponte._ao_pacote is not None:
                try:
                    ponte._ao_pacote(pacote)
                except Exception:
                    # Um consumidor que falha nao pode derrubar a ponte.
                    pass
            self._responder(204)

        def log_message(self, *args):  # noqa: D401
            """Silencio: o servidor nao polui o terminal do app."""
            return

    return _Handler
