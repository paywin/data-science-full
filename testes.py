"""Testes pequenos dos cálculos e das falhas que apareceram no projeto."""
import unittest
from unittest.mock import Mock, patch

import pandas as pd
import requests

import etl_covid
import etl_economia
import etl_impacto
import etl_tendencias


class Testes(unittest.TestCase):
    def test_media_movel_datas_e_crescimento(self):
        datas = list(pd.date_range("2020-01-01", periods=7)) + [pd.Timestamp("2020-02-01"), pd.Timestamp("2024-01-01")]
        dados = pd.DataFrame({"code": ["BRA"] * 9, "date": datas, "new_cases": range(1, 10), "total_cases": range(10, 100, 10)})
        resultado = etl_covid.transformar(dados)
        self.assertEqual(len(resultado), 8)
        self.assertEqual(resultado.iloc[6]["media_movel_7d"], 4)
        self.assertTrue(pd.isna(resultado.iloc[7]["media_movel_7d"]))
        self.assertTrue(pd.isna(resultado.iloc[7]["crescimento_casos_pct"]))
        self.assertEqual(resultado.iloc[1]["crescimento_casos_pct"], 100)

    def test_rejeita_datas_duplicadas(self):
        dados = pd.DataFrame({"code": ["BRA", "BRA"], "date": ["2020-01-01"] * 2, "new_cases": [1, 1], "total_cases": [1, 1]})
        with self.assertRaises(ValueError):
            etl_covid.transformar(dados)

    def test_economia_preserva_ausencias_e_cria_25_linhas(self):
        respostas = {}
        for codigo in etl_economia.INDICADORES:
            respostas[codigo] = [{"pages": 1}, [{"countryiso3code": "BRA", "date": "2020", "value": 10, "indicator": {"id": codigo}}]]
        economia = etl_economia.transformar(respostas)
        self.assertEqual(len(economia), 25)
        self.assertTrue(economia.query("pais_codigo == 'USA'")["desemprego_pct"].isna().all())

    def test_correlacoes_excluem_baixa_cobertura(self):
        base = pd.DataFrame({"ano": [2020] * 4, "cobertura_adequada": [True, True, True, False],
                             "casos_por_milhao": [1, 2, 3, 100], "pico_media_movel_por_milhao": [2, 4, 6, 200],
                             "crescimento_pib_real_pct": [3, 2, 1, 100], "desemprego_pct": [1, 2, 3, -100]})
        resultado = etl_impacto.correlacionar(base).iloc[0]
        self.assertEqual(resultado["observacoes"], 3)
        self.assertEqual(resultado["excluidos_baixa_cobertura"], 1)
        self.assertAlmostEqual(resultado["spearman_rho"], -1)

    def test_variacoes_nao_dividem_por_zero_nem_pulam_ano(self):
        base = pd.DataFrame({"pais_codigo": ["BRA"] * 3, "ano": [2019, 2020, 2022],
                             "casos_novos_ano": [0, 20, 30], "pib_usd_correntes": [100, 110, 120],
                             "crescimento_pib_real_pct": [2, -3, 4], "desemprego_pct": [8, 10, 9]})
        resultado = etl_tendencias.transformar(base)
        self.assertEqual(resultado.iloc[1]["variacao_desemprego_pct_pp"], 2)
        self.assertTrue(pd.isna(resultado.iloc[1]["variacao_casos_novos_ano_pct"]))
        self.assertTrue(pd.isna(resultado.iloc[2]["variacao_pib_usd_correntes_pct"]))

    @patch("etl_economia.time.sleep")
    @patch("etl_economia.requests.get")
    def test_timeout_tenta_novamente(self, get, sleep):
        resposta = Mock()
        codigo = "NY.GDP.MKTP.CD"
        resposta.json.return_value = [{"pages": 1}, [{"countryiso3code": "BRA", "date": "2020", "value": 10, "indicator": {"id": codigo}}]]
        get.side_effect = [requests.ReadTimeout(), resposta]
        self.assertEqual(etl_economia.buscar(codigo)[1][0]["value"], 10)
        self.assertEqual(get.call_count, 2)

    def test_api_vazia_nao_vira_dados_falsos(self):
        for resposta in [[], {}, [{"pages": 1}, None], [{"pages": 1}, []]]:
            with self.assertRaises(ValueError):
                etl_economia.validar(resposta, "NY.GDP.MKTP.CD")


if __name__ == "__main__":
    unittest.main()
