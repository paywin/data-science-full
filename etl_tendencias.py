"""Mateus: comparar a evolução dos casos, PIB e desemprego ao longo dos anos."""
import pandas as pd

from banco import DADOS, salvar


def transformar(base):
    if base.duplicated(["pais_codigo", "ano"]).any():
        raise ValueError("Existem países/anos duplicados na base integrada.")
    tabela = base.sort_values(["pais_codigo", "ano"]).reset_index(drop=True).copy()
    ano_anterior = tabela.groupby("pais_codigo")["ano"].shift(1)
    for coluna in ["casos_novos_ano", "pib_usd_correntes", "crescimento_pib_real_pct", "desemprego_pct"]:
        anterior = tabela.groupby("pais_codigo")[coluna].shift(1)
        anterior = anterior.where(tabela["ano"] - ano_anterior == 1)
        if coluna in ["crescimento_pib_real_pct", "desemprego_pct"]:
            # Exemplo: desemprego de 8% para 10% = aumento de 2 pontos percentuais.
            tabela[f"variacao_{coluna}_pp"] = tabela[coluna] - anterior
        else:
            # Divisão por zero ou valor ausente fica vazia.
            tabela[f"variacao_{coluna}_pct"] = (tabela[coluna] / anterior.where(anterior > 0) - 1) * 100
    return tabela


def executar(banco=None):
    base = pd.read_csv(DADOS / "base_integrada_pais_ano.csv")
    salvar(transformar(base), "tendencias_anual_pais", banco)


if __name__ == "__main__":
    executar()
