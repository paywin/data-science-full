"""Pessoa 4: calcula tendências e variações anuais a partir da base integrada."""

import argparse
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from infra import carregar_mongo, salvar_csv

RAIZ = Path(__file__).resolve().parents[1]
METRICAS = ("casos_novos_ano", "pico_media_movel_7d", "casos_acumulados_fim_ano",
            "pib_usd_correntes", "crescimento_pib_real_pct", "desemprego_pct")
TAXAS_PERCENTUAIS = {"crescimento_pib_real_pct", "desemprego_pct"}


def criar_tabelas(base: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Mantém uma linha por país/ano e variações em unidades adequadas."""
    obrigatorias = {"pais_codigo", "pais", "ano", "fase", *METRICAS}
    if obrigatorias - set(base.columns):
        raise ValueError(f"Base integrada sem colunas: {sorted(obrigatorias - set(base.columns))}")
    if base.duplicated(["pais_codigo", "ano"]).any():
        raise ValueError("Base integrada contém país/ano duplicado: corrija a origem.")
    base = base.copy()
    anos = pd.to_numeric(base["ano"], errors="raise")
    if anos.isna().any() or (anos % 1 != 0).any():
        raise ValueError("Ano inválido na base integrada")
    base["ano"] = anos.astype(int)
    anual = base.sort_values(["pais_codigo", "ano"]).reset_index(drop=True).copy()
    for coluna in METRICAS:
        anual[coluna] = pd.to_numeric(anual[coluna], errors="coerce")
    variacoes = anual[["pais_codigo", "pais", "ano", "fase"]].copy()
    for coluna in METRICAS:
        anterior = anual.groupby("pais_codigo")[coluna].shift(1)
        ano_anterior = anual.groupby("pais_codigo")["ano"].shift(1)
        anterior = anterior.where(anual["ano"] - ano_anterior == 1)
        referencia_2019 = anual.loc[anual["ano"] == 2019].set_index("pais_codigo")[coluna]
        base_referencia = anual["pais_codigo"].map(referencia_2019)
        diferenca = anual[coluna] - anterior
        variacoes[f"variacao_{coluna}_absoluta"] = diferenca
        variacoes[f"variacao_{coluna}_vs_2019"] = anual[coluna] - base_referencia
        if coluna in TAXAS_PERCENTUAIS:
            variacoes[f"variacao_{coluna}_pp"] = diferenca
        else:
            variacoes[f"variacao_{coluna}_pct"] = (
                (anual[coluna] / anterior.where(anterior > 0) - 1) * 100
            )
    return anual, variacoes, variacoes.loc[variacoes["ano"] == 2020].copy()


def executar_etl(entrada: Path | None = None, saida: Path | None = None) -> dict[str, Path]:
    origem = entrada or RAIZ / "dados" / "base_integrada_pais_ano.csv"
    destino = saida or RAIZ / "dados"
    anual, variacoes, choque = criar_tabelas(pd.read_csv(origem, encoding="utf-8-sig"))
    destino.mkdir(parents=True, exist_ok=True)
    arquivos = {"tendencias_anual_pais.csv": anual, "variacoes_anuais_pais.csv": variacoes,
                "choque_2020_vs_2019.csv": choque}
    for nome, tabela in arquivos.items():
        salvar_csv(tabela, destino / nome)
        carregar_mongo(tabela, Path(nome).stem, ["pais_codigo", "ano"])
        print(f"Tendências: {len(tabela)} registros -> {destino / nome}")
    return {nome: destino / nome for nome in arquivos}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-integrada", type=Path)
    parser.add_argument("--saida", type=Path)
    argumentos = parser.parse_args()
    executar_etl(argumentos.base_integrada, argumentos.saida)
