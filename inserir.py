import csv
import re

from neo4j import GraphDatabase

from config import DATA_DIR, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

TAM_LOTE = 5000


def ler_filmes():
    filmes = []
    with open(f"{DATA_DIR}/movies.csv", newline="", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            titulo = linha["title"].strip()
            achou = re.search(r"\((\d{4})\)\s*$", titulo)
            ano = int(achou.group(1)) if achou else None
            generos = [g for g in linha["genres"].split("|") if g != "(no genres listed)"]
            filmes.append(
                {
                    "movieId": int(linha["movieId"]),
                    "title": titulo,
                    "year": ano,
                    "genres": generos,
                }
            )
    return filmes


def ler_avaliacoes():
    avaliacoes = []
    with open(f"{DATA_DIR}/train.csv", newline="", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            avaliacoes.append(
                {
                    "userId": int(linha["userId"]),
                    "movieId": int(linha["movieId"]),
                    "rating": float(linha["rating"]),
                    "timestamp": int(linha["timestamp"]),
                }
            )
    return avaliacoes


def em_lotes(lista, tamanho):
    for i in range(0, len(lista), tamanho):
        yield lista[i : i + tamanho]


def main():
    filmes = ler_filmes()
    avaliacoes = ler_avaliacoes()

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as s:
        s.run("MATCH (n) CALL { WITH n DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS").consume()

        s.run("CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.userId IS UNIQUE").consume()
        s.run("CREATE CONSTRAINT movie_id IF NOT EXISTS FOR (m:Movie) REQUIRE m.movieId IS UNIQUE").consume()
        s.run("CREATE CONSTRAINT genre_name IF NOT EXISTS FOR (g:Genre) REQUIRE g.name IS UNIQUE").consume()

        for lote in em_lotes(filmes, TAM_LOTE):
            s.run(
                """
                UNWIND $rows AS row
                MERGE (m:Movie {movieId: row.movieId})
                SET m.title = row.title, m.year = row.year
                """,
                rows=lote,
            ).consume()
            s.run(
                """
                UNWIND $rows AS row
                MATCH (m:Movie {movieId: row.movieId})
                UNWIND row.genres AS nome
                MERGE (g:Genre {name: nome})
                MERGE (m)-[:HAS_GENRE]->(g)
                """,
                rows=lote,
            ).consume()
        print(f"{len(filmes)} filmes inseridos")

        feitos = 0
        for lote in em_lotes(avaliacoes, TAM_LOTE):
            s.run(
                """
                UNWIND $rows AS row
                MERGE (u:User {userId: row.userId})
                WITH u, row
                MATCH (m:Movie {movieId: row.movieId})
                CREATE (u)-[:RATED {rating: row.rating, timestamp: row.timestamp}]->(m)
                """,
                rows=lote,
            ).consume()
            feitos += len(lote)
            print(f"{feitos}/{len(avaliacoes)} avaliacoes")

        s.run(
            """
            MATCH (m:Movie)<-[r:RATED]-()
            WITH m, avg(r.rating) AS media, count(r) AS qtd
            SET m.avgRating = media, m.numRatings = qtd
            """
        ).consume()
        s.run(
            """
            MATCH (u:User)-[r:RATED]->()
            WITH u, avg(r.rating) AS media, count(r) AS qtd
            SET u.avgRating = media, u.numRatings = qtd
            """
        ).consume()
    driver.close()
    print("pronto")


if __name__ == "__main__":
    main()
