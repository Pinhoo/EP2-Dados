import csv
import math

from neo4j import GraphDatabase

from config import (
    DATA_DIR,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    VIZINHOS_NO_GRAFO,
    MIN_CO_AVALIACOES,
)

TAM_LOTE = 5000


def carregar_treino():
    por_filme = {}
    with open(f"{DATA_DIR}/train.csv", newline="", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            u = int(linha["userId"])
            m = int(linha["movieId"])
            por_filme.setdefault(m, {})[u] = float(linha["rating"])
    return por_filme


def preparar(por_filme):
    medias = {m: sum(r.values()) / len(r) for m, r in por_filme.items()}
    desvios_filme = {}
    desvios_usuario = {}
    for m, notas in por_filme.items():
        lista = []
        for u, nota in notas.items():
            d = nota - medias[m]
            lista.append((u, d))
            desvios_usuario.setdefault(u, []).append((m, d))
        desvios_filme[m] = lista
    return desvios_filme, desvios_usuario


def vizinhos_do_filme(i, desvios_filme, desvios_usuario):
    acc = {}
    for u, di in desvios_filme[i]:
        for j, dj in desvios_usuario[u]:
            if j == i:
                continue
            a = acc.get(j)
            if a is None:
                acc[j] = [di * dj, di * di, dj * dj, 1]
            else:
                a[0] += di * dj
                a[1] += di * di
                a[2] += dj * dj
                a[3] += 1

    resultado = []
    for j, (num, si, sj, n) in acc.items():
        if n < MIN_CO_AVALIACOES:
            continue
        den = math.sqrt(si) * math.sqrt(sj)
        if den == 0:
            continue
        resultado.append((j, num / den, n))

    resultado.sort(key=lambda x: abs(x[1]), reverse=True)
    return resultado[:VIZINHOS_NO_GRAFO]


def gravar(session, linhas):
    session.run(
        """
        UNWIND $rows AS row
        MATCH (a:Movie {movieId: row.a}), (b:Movie {movieId: row.b})
        CREATE (a)-[:SIMILAR {corr: row.corr, coRaters: row.n}]->(b)
        """,
        rows=linhas,
    ).consume()


def main():
    por_filme = carregar_treino()
    desvios_filme, desvios_usuario = preparar(por_filme)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as s:
        s.run("MATCH ()-[r:SIMILAR]->() CALL { WITH r DELETE r } IN TRANSACTIONS OF 10000 ROWS").consume()

        buffer = []
        total = 0
        for idx, i in enumerate(desvios_filme, start=1):
            for j, corr, n in vizinhos_do_filme(i, desvios_filme, desvios_usuario):
                buffer.append({"a": i, "b": j, "corr": corr, "n": n})
            if len(buffer) >= TAM_LOTE:
                gravar(s, buffer)
                total += len(buffer)
                buffer = []
            if idx % 500 == 0:
                print(f"{idx}/{len(desvios_filme)} filmes processados")
        if buffer:
            gravar(s, buffer)
            total += len(buffer)
    driver.close()
    print(f"{total} arestas SIMILAR criadas")


if __name__ == "__main__":
    main()
