"""Testes sem internet do contrato de dados e das quatro etapas."""

import unittest
from unittest.mock import patch

import pandas as pd

from pessoa1_covid.etl_covid import transformar_covid
from pessoa2_economia.etl_economia import INDICADORES, buscar_indicador, montar_economia
from pessoa3_impacto.etl_impacto import integrar_dados, calcular_correlacoes, comparar_2020
from pessoa4_tendencias.etl_tendencias import criar_tabelas


class TestesETL(unittest.TestCase):
    def setUp(self):
        paises = ["BRA", "USA", "CHN", "DEU", "IND"]
        self.covid = pd.DataFrame([
            {"code": pais, "country": pais, "date": f"{ano}-06-01", "new_cases": 10 + i,
             "total_cases": 100 + i + (ano - 2020) * 50}
            for i, pais in enumerate(paises) for ano in range(2020, 2024)
        ])
        self.economia = pd.DataFrame([
            {"pais_codigo": pais, "ano": ano, "pib_usd": 1000 + i * 100 + (ano - 2019) * 10,
             "desemprego_percentual": 5 + i + (ano - 2019) * 0.5,
             "pib_crescimento_real_pct": -2 + i + (ano - 2019), "populacao": 1_000_000}
            for i, pais in enumerate(paises) for ano in range(2019, 2024)
        ])

    def test_covid_padroniza_e_calcula_media(self):
        tabela = transformar_covid(self.covid)
        self.assertIn("casos_novos", tabela)
        self.assertIn("crescimento_casos_pct", tabela)
        self.assertEqual(len(tabela), 20)
        self.assertEqual(tabela.loc[tabela["pais_codigo"] == "BRA", "casos_novos"].iloc[0], 10)

    def test_covid_rejeita_duplicados(self):
        with self.assertRaisesRegex(ValueError, "duplicados"):
            transformar_covid(pd.concat([self.covid, self.covid.iloc[[0]]]))

    def test_economia_cria_grade_e_preserva_ausencias(self):
        tabelas = {}
        for coluna in INDICADORES.values():
            tabelas[coluna] = pd.DataFrame({"pais_codigo": ["BRA"], "ano": [2019], coluna: [3.5]})
        economia = montar_economia(tabelas)
        self.assertEqual(len(economia), 25)
        self.assertTrue(pd.isna(economia.query("pais_codigo == 'USA' and ano == 2020")["desemprego_pct"].iloc[0]))

    def test_api_rejeita_lista_vazia(self):
        from pessoa2_economia.etl_economia import validar_resposta
        with self.assertRaises(ValueError):
            validar_resposta(b'[{"pages": 1}, null]')

    def test_integracao_legada_e_variacoes(self):
        base = integrar_dados(self.covid, self.economia)
        self.assertEqual(len(base), 25)
        self.assertEqual(base.groupby(["pais_codigo", "ano"]).size().max(), 1)
        referencia = base.query("ano == 2019")
        self.assertTrue(referencia["cobertura_covid"].isna().all())
        self.assertTrue((referencia["covid_observado"] == 0).all())
        self.assertTrue((referencia["casos_novos_ano"] == 0).all())
        self.assertEqual(len(comparar_2020(base)), 5)
        self.assertEqual(len(calcular_correlacoes(base)), 20)
        anual, variacoes, choque = criar_tabelas(base)
        self.assertEqual((len(anual), len(variacoes), len(choque)), (25, 25, 5))
        self.assertTrue(variacoes.query("ano == 2020")["variacao_casos_novos_ano_pct"].isna().all())
        self.assertIn("variacao_desemprego_pct_pp", variacoes)

    def test_integracao_rejeita_pais_ano_duplicado(self):
        with self.assertRaisesRegex(ValueError, "duplicado"):
            integrar_dados(self.covid, pd.concat([self.economia, self.economia.iloc[[0]]]))


if __name__ == "__main__":
    unittest.main()
