Warning: fs was declared with const; use let for reassignable variables.
"""
Analise integrada: COVID-19 x indicadores economicos (Pessoas 1 e 2).

Entradas (mesma pasta ou caminhos abaixo):
  - covid.csv                       (ETL da Pessoa 1)
  - economia_paises_2019_2023.csv   (ETL da Pessoa 2, v2 com crescimento real e populacao)

Saidas:
  - base_integrada_pais_ano.csv     (1 linha por pais/ano, COVID + economia)
  - correlacoes.csv                 (Pearson e Spearman, com n e p-valor)
  - variacao_2020_vs_2019.csv       (choque economico x casos por pais)

Uso:  python analise_integrada.py
Requisitos: pip install pandas scipy
"""
from pathlib import Path
import pandas as pd
from scipy import stats

PASTA = Path(__file__).resolve().parent
COVID = PASTA / "covid.csv"
ECONOMIA = PASTA / "economia_paises_2019_2023.csv"
ANOS = range(2019, 2024)
PAISES = {"BRA": "Brasil", "USA": "Estados Unidos", "CHN": "China",
          "DEU": "Alemanha", "IND": "India"}


def covid_anual() -> pd.DataFrame:
    df = pd.read_csv(COVID, parse_dates=["date"])
    df["ano"] = df["date"].dt.year
    df = df[df["ano"].isin(ANOS)]
    g = df.groupby(["code", "ano"])
    out = g.agg(
        casos_novos=("new_cases", lambda s: s.sum(min_count=1)),  # NaN se tudo ausente
        dias_com_dado=("new_cases", "count"),
        dias_no_ano=("date", "size"),
        pico_media_7d=("media_movel_7d", "max"),
    ).reset_index().rename(columns={"code": "pais_codigo"})
    # 2019: a fonte comeca em 2020-01-01, entao nao ha registro -> casos = 0 (pre-pandemia)
    grade = pd.MultiIndex.from_product([PAISES, ANOS], names=["pais_codigo", "ano"]).to_frame(index=False)
    out = grade.merge(out, how="left", on=["pais_codigo", "ano"])
    pre = out["ano"] == 2019
    out.loc[pre, ["casos_novos", "pico_media_7d"]] = 0
    out["cobertura_dados"] = (out["dias_com_dado"] / out["dias_no_ano"]).round(2)
    out.loc[pre, "cobertura_dados"] = 1.0
    return out.drop(columns=["dias_com_dado", "dias_no_ano"])


def integrar() -> pd.DataFrame:
    eco = pd.read_csv(ECONOMIA)
    base = covid_anual().merge(eco.drop(columns=["pais"], errors="ignore"),
                               how="left", on=["pais_codigo", "ano"])
    base.insert(1, "pais", base["pais_codigo"].map(PAISES))
    # PIB: crescimento % ano a ano, calculado dentro de cada pais (PIB em US$ correntes
    # sofre efeito cambial; use com cautela e prefira o crescimento real se disponivel)
    base = base.sort_values(["pais_codigo", "ano"])
    base["pib_var_pct"] = base.groupby("pais_codigo")["pib_usd"].pct_change() * 100
    # Preferir crescimento REAL (ETL v2). Se nao existir, usa a variacao do PIB em US$.
    base["pib_crescimento"] = base.get("pib_crescimento_real_pct", base["pib_var_pct"])
    if "populacao" in base.columns:
        base["casos_por_milhao"] = base["casos_novos"] / base["populacao"] * 1e6
        base["pico_7d_por_milhao"] = base["pico_media_7d"] / base["populacao"] * 1e6
    return base


def correlacoes(base: pd.DataFrame) -> pd.DataFrame:
    covid = [c for c in ("casos_por_milhao", "pico_7d_por_milhao") if c in base.columns] \
        or ["casos_novos", "pico_media_7d"]
    eco = ["pib_crescimento", "desemprego_percentual"]
    pares = [(x, y) for x in covid for y in eco]
    linhas = []
    for x, y in pares:
        d = base[[x, y]].dropna()
        if len(d) < 4:
            continue
        r, p = stats.pearsonr(d[x], d[y])
        rho, ps = stats.spearmanr(d[x], d[y])
        linhas.append({"x": x, "y": y, "n": len(d), "pearson_r": round(r, 3),
                       "pearson_p": round(p, 3), "spearman_rho": round(rho, 3),
                       "spearman_p": round(ps, 3)})
    return pd.DataFrame(linhas)


def variacao_2020(base: pd.DataFrame) -> pd.DataFrame:
    casos = "casos_por_milhao" if "casos_por_milhao" in base.columns else "casos_novos"
    p = base.pivot(index="pais", columns="ano", values=["desemprego_percentual", "pib_crescimento", casos])
    return pd.DataFrame({
        "delta_desemprego_pp_2020": p[("desemprego_percentual", 2020)] - p[("desemprego_percentual", 2019)],
        "pib_crescimento_2020": p[("pib_crescimento", 2020)],
        casos + "_2020": p[(casos, 2020)],
    }).reset_index()


if __name__ == "__main__":
    base = integrar()
    base.to_csv(PASTA / "base_integrada_pais_ano.csv", index=False, encoding="utf-8-sig")
    cor = correlacoes(base)
    cor.to_csv(PASTA / "correlacoes.csv", index=False, encoding="utf-8-sig")
    variacao_2020(base).to_csv(PASTA / "variacao_2020_vs_2019.csv", index=False, encoding="utf-8-sig")
    print(base.round(2).to_string(index=False))
    print("\nCorrelacoes (n pequeno: leia com cautela):")
    print(cor.to_string(index=False))
