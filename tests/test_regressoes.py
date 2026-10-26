"""Regressões dos erros de execução e de integridade identificados na revisão."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
import requests

from infra import obter, carregar_mongo
from pessoa1_covid.etl_covid import transformar_covid
from pessoa2_economia.etl_economia import buscar_indicador, validar_resposta
from pessoa3_impacto.etl_impacto import calcular_correlacoes, agregar_covid
from pessoa4_tendencias.etl_tendencias import criar_tabelas, METRICAS


class Regressao(unittest.TestCase):
    def test_janela_calendario_crescimento_e_recorte(self):
        datas = list(pd.date_range('2020-01-01', periods=7)) + [pd.Timestamp('2020-02-01'), pd.Timestamp('2024-01-01')]
        fonte = pd.DataFrame({'code': ['BRA'] * 9, 'date': datas, 'new_cases': list(range(1, 10)), 'total_cases': list(range(10, 100, 10))})
        resultado = transformar_covid(fonte)
        self.assertEqual(len(resultado), 8)
        self.assertEqual(resultado.iloc[6]['media_movel_7d'], 4)
        self.assertTrue(pd.isna(resultado.iloc[7]['media_movel_7d']))
        self.assertTrue(pd.isna(resultado.iloc[7]['crescimento_casos_pct']))
        self.assertEqual(resultado.iloc[1]['crescimento_casos_pct'], 100)

    def test_media_recalculada_e_acumulado_sem_31_dezembro(self):
        fonte = pd.DataFrame({'code': ['BRA'], 'date': ['2020-06-01'], 'new_cases': [10], 'total_cases': [100], 'media_movel_7d': [999]})
        anual = agregar_covid(fonte).iloc[0]
        self.assertTrue(pd.isna(anual['casos_acumulados_fim_ano']))
        self.assertTrue(pd.isna(anual['pico_media_movel_7d']))
        self.assertAlmostEqual(anual['cobertura_covid'], 1 / 366)

    def test_correlacao_filtra_cobertura_e_calcula_spearman(self):
        base = pd.DataFrame({'ano': [2020]*4, 'covid_observado': [1]*4, 'cobertura_covid': [1, 1, 1, .1],
                             'casos_por_milhao': [1, 2, 3, 100], 'pico_media_movel_por_milhao': [2, 4, 6, 200],
                             'crescimento_pib_real_pct': [3, 2, 1, 100], 'desemprego_pct': [1, 2, 3, -100]})
        resultado = calcular_correlacoes(base).iloc[0]
        self.assertEqual(resultado['observacoes'], 3)
        self.assertEqual(resultado['excluidos_baixa_cobertura'], 1)
        self.assertAlmostEqual(resultado['spearman_rho'], -1)
        with self.assertRaises(ValueError):
            calcular_correlacoes(base, 2)

    @patch('infra.time.sleep')
    @patch('infra.requests.get')
    def test_timeout_retry_cache_e_sem_rede_na_reexecucao(self, get, sleep):
        resposta = MagicMock()
        resposta.__enter__.return_value = resposta
        resposta.content = b'{"ok":true}'
        get.side_effect = [requests.ReadTimeout(), resposta]
        with tempfile.TemporaryDirectory() as pasta, patch.dict(os.environ, {'ETL_ATUALIZAR':'0'}):
            cache = Path(pasta)/'fonte.json'
            self.assertEqual(obter('https://exemplo.invalid', cache=cache, validar=json.loads), resposta.content)
            self.assertTrue(cache.exists())
            self.assertEqual(get.call_count, 2)
            obter('https://exemplo.invalid', cache=cache, validar=json.loads)
            self.assertEqual(get.call_count, 2)

    @patch('infra.time.sleep')
    @patch('infra.requests.get')
    def test_falha_preserva_cache_e_nao_mascara_atualizacao(self, get, sleep):
        get.side_effect = requests.ReadTimeout()
        with tempfile.TemporaryDirectory() as pasta, patch.dict(os.environ, {'ETL_ATUALIZAR':'1'}):
            cache = Path(pasta)/'fonte.json'
            cache.write_bytes(b'original')
            with self.assertRaises(RuntimeError):
                obter('https://exemplo.invalid', cache=cache)
            self.assertEqual(cache.read_bytes(), b'original')
            self.assertEqual(get.call_count, 3)

    @patch('pessoa2_economia.etl_economia.obter')
    def test_api_multiplos_paises_paginacao(self, obter_mock):
        paises = ['BRA','USA','CHN','DEU','IND']
        itens = [{'countryiso3code': p, 'date': '2020', 'value': i, 'indicator': {'id':'NY.GDP.MKTP.CD'}} for i,p in enumerate(paises)]
        obter_mock.side_effect = [json.dumps([{'pages':2}, itens[:3]]).encode(), json.dumps([{'pages':2}, itens[3:]]).encode()]
        tabela = buscar_indicador('NY.GDP.MKTP.CD', 'pib_usd_correntes')
        self.assertEqual(len(tabela), 5)
        self.assertEqual(obter_mock.call_count, 2)
        self.assertEqual(obter_mock.call_args.kwargs['params']['page'], 2)

    def test_api_rejeita_payload_invalido(self):
        for payload in [b'{}', b'[]', b'[{"pages":1},[]]', b'[{"pages":1},[{"date":"2020","value":1}]]']:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                validar_resposta(payload)

    def test_variacao_anual_nao_pula_ano_ausente(self):
        dados = {'pais_codigo':['BRA','BRA'], 'pais':['Brasil','Brasil'], 'ano':[2019,2021], 'fase':['Pré-pandemia','Fase crítica']}
        dados.update({m:[10,20] for m in METRICAS})
        _, variacoes, _ = criar_tabelas(pd.DataFrame(dados))
        self.assertTrue(pd.isna(variacoes.iloc[1]['variacao_pib_usd_correntes_pct']))
        self.assertEqual(variacoes.iloc[1]['variacao_pib_usd_correntes_vs_2019'], 10)


@unittest.skipUnless(os.getenv('MONGO_TEST_URI'), 'Defina MONGO_TEST_URI para testar MongoDB real')
class MongoReal(unittest.TestCase):
    def test_reexecucao_atualiza_remove_obsoletos_e_preserva_nulos(self):
        import uuid
        from pymongo import MongoClient
        banco = 'teste_etl_' + uuid.uuid4().hex
        uri = os.environ['MONGO_TEST_URI']
        with patch.dict(os.environ, {'MONGODB_URI':uri, 'MONGODB_DATABASE':banco, 'ETL_SEM_MONGO':'0'}):
            with MongoClient(uri) as cliente:
                try:
                    tabela = pd.DataFrame({'pais':['BRA','USA'], 'valor':[1, float('nan')]})
                    carregar_mongo(tabela, 'exemplo', ['pais'])
                    carregar_mongo(tabela, 'exemplo', ['pais'])
                    self.assertEqual(cliente[banco].exemplo.count_documents({}), 2)
                    self.assertIsNone(cliente[banco].exemplo.find_one({'pais':'USA'})['valor'])
                    carregar_mongo(pd.DataFrame({'pais':['BRA'], 'valor':[9]}), 'exemplo', ['pais'])
                    self.assertEqual(cliente[banco].exemplo.count_documents({}), 1)
                    self.assertEqual(cliente[banco].exemplo.find_one({'pais':'BRA'})['valor'], 9)
                    with self.assertRaises(ValueError):
                        carregar_mongo(pd.DataFrame({'pais':['BRA','BRA']}), 'exemplo', ['pais'])
                    self.assertEqual(cliente[banco].exemplo.count_documents({}), 1)
                finally:
                    cliente.drop_database(banco)
