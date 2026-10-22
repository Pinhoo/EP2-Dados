import csv
import math

from neo4j import GraphDatabase

from config import (
    DATA_DIR,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    LIMIAR_RELEVANTE,
    TOP_N,
)
from recomendar import prever, recomendar


def carregar_teste():
    por_usuario = {}
    with open(f"{DATA_DIR}/test.csv", newline="", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            u = int(linha["userId"])
            por_usuario.setdefault(u, []).append((int(linha["movieId"]), float(linha["rating"])))
    return por_usuario


def main():
    teste = carregar_teste()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    precisoes = []
    recalls = []
    erros_abs = []
    erros_quad = []

    with driver.session() as s:
        for idx, (usuario, itens) in enumerate(teste.items(), start=1):
            relevantes = {m for m, nota in itens if nota >= LIMIAR_RELEVANTE}
            if relevantes:
                recs = recomendar(s, usuario, TOP_N)
                ids = {r["movieId"] for r in recs}
                acertos = len(ids & relevantes)
                precisoes.append(acertos / TOP_N)
                recalls.append(acertos / len(relevantes))

            for filme, nota in itens:
                previsto = prever(s, usuario, filme)
                erro = previsto - nota
                erros_abs.append(abs(erro))
                erros_quad.append(erro * erro)

            if idx % 50 == 0:
                print(f"{idx}/{len(teste)} usuarios avaliados")
    driver.close()

    print(f"\nusuarios com algum filme relevante no teste: {len(precisoes)}")
    print(f"precisao@{TOP_N}: {sum(precisoes) / len(precisoes):.4f}")
    print(f"recall@{TOP_N}:   {sum(recalls) / len(recalls):.4f}")
    print(f"MAE:  {sum(erros_abs) / len(erros_abs):.4f}")
    print(f"RMSE: {math.sqrt(sum(erros_quad) / len(erros_quad)):.4f}")


if __name__ == "__main__":
    main()
