"""
Testes do parser SSE e do formato do pacote da sessao pareada.

O parser e puro: recebe as linhas cruas do `text/event-stream` e devolve os
eventos. E o pedaco que mais falha em silencio (moldura sem linha em branco,
`data:` multi-linha, comentario `: ping`), entao vira teste.
"""

from __future__ import annotations

import unittest

from ai.sessao_pareada import AcumuladorSSE, parsear_evento_sse


class TestParserSSE(unittest.TestCase):
    def test_um_evento_completo(self):
        linhas = [
            "event: aberta",
            'data: {"tipo":"aberta","em":1,"dados":{"id":"x"}}',
            "",
        ]
        eventos = list(parsear_evento_sse(linhas))
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["tipo"], "aberta")
        self.assertEqual(eventos[0]["dados"]["id"], "x")

    def test_varios_eventos_e_ping_ignorado(self):
        linhas = [
            ": ping",
            "event: pareada",
            'data: {"tipo":"pareada","em":2}',
            "",
            ": ping",
            "event: turno",
            'data: {"tipo":"turno","em":3,"dados":{"resposta":{"fala":"oi"}}}',
            "",
        ]
        eventos = list(parsear_evento_sse(linhas))
        self.assertEqual([e["tipo"] for e in eventos], ["pareada", "turno"])
        self.assertEqual(eventos[1]["dados"]["resposta"]["fala"], "oi")

    def test_data_sem_tipo_usa_o_event(self):
        linhas = ["event: fechada", "data: {\"em\":9}", ""]
        eventos = list(parsear_evento_sse(linhas))
        self.assertEqual(eventos[0]["tipo"], "fechada")

    def test_moldura_sem_linha_em_branco_no_fim(self):
        linhas = ["event: turno", 'data: {"tipo":"turno","em":5}']
        eventos = list(parsear_evento_sse(linhas))
        self.assertEqual(len(eventos), 1)
        self.assertEqual(eventos[0]["tipo"], "turno")

    def test_json_invalido_nao_derruba_e_vira_bruto(self):
        linhas = ["event: turno", "data: isto nao e json", ""]
        eventos = list(parsear_evento_sse(linhas))
        self.assertEqual(eventos[0]["tipo"], "turno")
        self.assertIn("bruto", eventos[0])

    def test_data_multilinha(self):
        linhas = ["data: {", 'data: "tipo": "turno"', "data: }", ""]
        eventos = list(parsear_evento_sse(linhas))
        self.assertEqual(eventos[0]["tipo"], "turno")

    def test_acumulador_nao_emite_em_linha_solta(self):
        acc = AcumuladorSSE()
        self.assertIsNone(acc.linha("event: turno"))
        self.assertIsNone(acc.linha('data: {"tipo":"turno"}'))
        evento = acc.linha("")
        self.assertEqual(evento["tipo"], "turno")


if __name__ == "__main__":
    unittest.main()
