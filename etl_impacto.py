"""Luiz: juntar COVID e economia e calcular correlações descritivas."""
import pandas as pd

from banco import DADOS, salvar
from etl_covid import transformar as transformar_covid


def integrar(covid, economia):
    covid = transformar_covid(covid)
    covid["ano"] = covid["data"].dt.year
    anual = covid.groupby(["pais_codigo", "ano"], as_index=False).agg(
        casos_novos_ano=("casos_novos", lambda valores: valores.sum(min_count=1)),
        pico_media_movel_7d=("media_movel_7d", "max"),
        dias_com_dados=("casos_novos", "count"),
    )
    dias_no_ano = pd.to_datetime(anual["ano"].astype(str) + "-01-01").dt.is_leap_year.map({True: 366, False: 365})
    anual["cobertura_covid"] = anual["dias_com_dados"] / dias_no_ano
    base = economia.merge(anual, on=["pais_codigo", "ano"], how="left", validate="one_to_one")
    base = base.sort_values(["pais_codigo", "ano"]).reset_index(drop=True)
    # Zero em 2019 é uma referência pré-pandemia, não uma observação diária.
    base.loc[base["ano"] == 2019, ["casos_novos_ano", "pico_media_movel_7d"]] = 0
    base["covid_observado"] = base["dias_com_dados"].fillna(0).gt(0)
    base["cobertura_adequada"] = base["cobertura_covid"].ge(0.9)
    populacao = base["populacao"].where(base["populacao"] > 0)
    base["casos_por_milhao"] = base["casos_novos_ano"] / populacao * 1_000_000
    base["pico_media_movel_por_milhao"] = base["pico_media_movel_7d"] / populacao * 1_000_000
    return base.drop(columns="dias_com_dados")


def correlacionar(base):
    resultados = []
    # Comparar apenas anos com pelo menos 90% dos dias preenchidos.
    pandemia = base[base["ano"].between(2020, 2023)]
    grupos = [("geral", "2020-2023", pandemia)]
    grupos += [("anual", str(ano), pandemia[pandemia["ano"] == ano]) for ano in range(2020, 2024)]
    for escopo, ano, grupo in grupos:
        completos = grupo[grupo["cobertura_adequada"]]
        for covid in ["casos_por_milhao", "pico_media_movel_por_milhao"]:
            for economia in ["crescimento_pib_real_pct", "desemprego_pct"]:
                pares = completos[[covid, economia]].dropna()
                pearson = spearman = float("nan")
                if len(pares) >= 3 and pares[covid].nunique() > 1 and pares[economia].nunique() > 1:
                    pearson = pares[covid].corr(pares[economia], method="pearson")
                    spearman = pares[covid].corr(pares[economia], method="spearman")
                resultados.append({"escopo": escopo, "ano": ano, "indicador_covid": covid,
                                   "indicador_economico": economia, "observacoes": len(pares),
                                   "excluidos_baixa_cobertura": len(grupo) - len(completos),
                                   "pearson_r": pearson, "spearman_rho": spearman})
    return pd.DataFrame(resultados)


def executar(banco=None):
    covid = pd.read_csv(DADOS / "covid.csv")
    economia = pd.read_csv(DADOS / "economia_paises_2019_2023.csv")
    base = integrar(covid, economia)
    salvar(base, "base_integrada_pais_ano", banco)
    salvar(correlacionar(base), "correlacoes", banco)


if __name__ == "__main__":
    executar()
