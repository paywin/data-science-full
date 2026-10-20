"""Executa os ETLs na ordem: COVID, economia, impacto e tendências."""

import argparse
from pathlib import Path
import subprocess
import sys

RAIZ = Path(__file__).resolve().parent
DADOS = RAIZ / "dados"


def executar(comando: list[str]) -> None:
    print("\n> " + " ".join(comando), flush=True)
    subprocess.run(comando, cwd=RAIZ, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--usar-arquivos-existentes", action="store_true",
                        help="Pula downloads; usa dados/covid.csv e dados/economia_paises_2019_2023.csv")
    parser.add_argument("--covid-local", type=Path,
                        help="Usa CSV local de COVID no lugar do download, mantendo o ETL 1")
    argumentos = parser.parse_args()
    python = sys.executable
    if argumentos.usar_arquivos_existentes and argumentos.covid_local:
        parser.error("Escolha --usar-arquivos-existentes ou --covid-local, não ambos.")
    if not argumentos.usar_arquivos_existentes:
        comando_covid = [python, "pessoa1_covid/etl_covid.py"]
        if argumentos.covid_local:
            comando_covid += ["--entrada", str(argumentos.covid_local.resolve())]
        executar(comando_covid)
        executar([python, "pessoa2_economia/etl_economia.py"])
    else:
        for nome in ("covid.csv", "economia_paises_2019_2023.csv"):
            if not (DADOS / nome).is_file():
                parser.error(f"Arquivo necessário não encontrado: {DADOS / nome}")
    executar([python, "pessoa3_impacto/etl_impacto.py"])
    executar([python, "pessoa4_tendencias/etl_tendencias.py"])
    print("\nProjeto finalizado. Os CSVs para o dashboard estão em dados/.")


if __name__ == "__main__":
    main()
