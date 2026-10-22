import csv
import random

from config import DATA_DIR, SEED


def main():
    with open(f"{DATA_DIR}/ratings.csv", newline="", encoding="utf-8") as f:
        leitor = csv.reader(f)
        cabecalho = next(leitor)
        linhas = list(leitor)

    random.Random(SEED).shuffle(linhas)
    corte = int(len(linhas) * 0.8)

    partes = (("train.csv", linhas[:corte]), ("test.csv", linhas[corte:]))
    for nome, parte in partes:
        with open(f"{DATA_DIR}/{nome}", "w", newline="", encoding="utf-8") as f:
            escritor = csv.writer(f)
            escritor.writerow(cabecalho)
            escritor.writerows(parte)
        print(f"{nome}: {len(parte)} avaliacoes")


if __name__ == "__main__":
    main()
