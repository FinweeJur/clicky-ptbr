"""
Testes da ponte local: geometria (pura) e um ciclo real no loopback.

O teste de ciclo sobe um `PonteLocal` numa porta efemera, faz um POST igual ao
que o navegador faria e confere que o ultimo pacote e a coordenada de tela
saem certos. Tambem confere o preflight de Private Network Access — sem ele o
Chrome bloqueia a pagina publica de falar com 127.0.0.1.
"""

from __future__ import annotations

import json
import unittest
import urllib.error
import urllib.request

from ponte.geometria import (
    ORIGENS_PADRAO,
    cabecalhos_cors,
    coordenadas_do_alvo,
    coordenadas_do_botao_abrir,
    origem_permitida,
)
from ponte.servidor import PonteLocal

ORIGEM = ORIGENS_PADRAO[0]

PACOTE = {
    "sessaoId": "s1",
    "url": "https://www.controlepopular.com.br/betim",
    "origem": {"x": 120, "y": 90},
    "viewport": {"largura": 1280, "altura": 720, "dpr": 1.5},
    "alvos": [
        {"tipo": "fonte", "indice": 1,
         "retangulo": {"x": 40, "y": 300, "largura": 18, "altura": 16}, "visivel": True},
        {"tipo": "fonte", "indice": 2,
         "retangulo": {"x": 40, "y": 9999, "largura": 18, "altura": 16}, "visivel": False},
        {"tipo": "abrir-pagina",
         "retangulo": {"x": 40, "y": 340, "largura": 120, "altura": 28}, "visivel": True},
    ],
    "em": 1727650000000,
}


class TestGeometria(unittest.TestCase):
    def test_origem_permitida_exige_match_exato(self):
        self.assertEqual(origem_permitida(ORIGEM), ORIGEM)
        # Barra no fim nao muda a origem.
        self.assertEqual(origem_permitida(ORIGEM + "/"), ORIGEM)
        # Origem estranha nao passa.
        self.assertIsNone(origem_permitida("https://exemplo.com"))

    def test_cabecalhos_cors_trazem_pna_para_origem_do_portal(self):
        cab = cabecalhos_cors(ORIGEM)
        self.assertEqual(cab["Access-Control-Allow-Origin"], ORIGEM)
        self.assertEqual(cab["Access-Control-Allow-Private-Network"], "true")

    def test_cabecalhos_cors_recusam_origem_desconhecida(self):
        cab = cabecalhos_cors("https://exemplo.com")
        self.assertNotIn("Access-Control-Allow-Origin", cab)
        self.assertNotIn("Access-Control-Allow-Private-Network", cab)

    def test_coordenada_do_indice_soma_a_origem_do_viewport(self):
        # centro = (40 + 18/2, 300 + 16/2) = (49, 308); + origem (120, 90).
        self.assertEqual(coordenadas_do_alvo(PACOTE, 1), (169.0, 398.0))

    def test_alvo_invisivel_nao_tem_coordenada(self):
        self.assertIsNone(coordenadas_do_alvo(PACOTE, 2))

    def test_indice_inexistente_nao_tem_coordenada(self):
        self.assertIsNone(coordenadas_do_alvo(PACOTE, 99))
        self.assertIsNone(coordenadas_do_alvo(None, 1))

    def test_coordenada_do_botao_abrir(self):
        # centro = (40 + 60, 340 + 14) = (100, 354); + origem -> (220, 444).
        self.assertEqual(coordenadas_do_botao_abrir(PACOTE), (220.0, 444.0))


class TestServidorLoopback(unittest.TestCase):
    def setUp(self):
        self.ponte = PonteLocal(porta=0)
        self.ponte.iniciar()
        self.porta = self.ponte._servidor.server_address[1]
        self.url = f"http://127.0.0.1:{self.porta}/ponte"

    def tearDown(self):
        self.ponte.parar()

    def test_post_guarda_o_ultimo_pacote(self):
        req = urllib.request.Request(
            self.url,
            data=json.dumps(PACOTE).encode("utf-8"),
            headers={"Content-Type": "application/json", "Origin": ORIGEM},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 204)
        self.assertEqual(self.ponte.ultimo["url"], PACOTE["url"])
        self.assertEqual(self.ponte.coordenadas_do_indice(1), (169.0, 398.0))

    def test_preflight_responde_pna(self):
        req = urllib.request.Request(
            self.url,
            headers={
                "Origin": ORIGEM,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Private-Network": "true",
            },
            method="OPTIONS",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 204)
            self.assertEqual(
                resp.headers.get("Access-Control-Allow-Private-Network"), "true"
            )
            self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), ORIGEM)

    def test_json_invalido_devolve_400(self):
        req = urllib.request.Request(
            self.url,
            data=b"nao e json",
            headers={"Content-Type": "application/json", "Origin": ORIGEM},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
