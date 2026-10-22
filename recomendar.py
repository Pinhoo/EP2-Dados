import argparse

from neo4j import GraphDatabase

from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, K_VIZINHOS, TOP_N

Q_VIZINHOS_AVALIADOS = """
MATCH (i:Movie {movieId: $filme})-[s:SIMILAR]->(j:Movie)<-[r:RATED]-(u:User {userId: $usuario})
RETURN s.corr AS corr, r.rating AS nota
ORDER BY abs(s.corr) DESC
LIMIT $k
"""

Q_MEDIA_FILME = "MATCH (m:Movie {movieId: $filme}) RETURN m.avgRating AS media"
Q_MEDIA_USUARIO = "MATCH (u:User {userId: $usuario}) RETURN u.avgRating AS media"

Q_RECOMENDAR = """
MATCH (u:User {userId: $usuario})-[r:RATED]->(j:Movie)<-[s:SIMILAR]-(i:Movie)
WHERE NOT (u)-[:RATED]->(i)
WITH i, sum(s.corr * r.rating) AS num, sum(abs(s.corr)) AS den, count(*) AS vizinhos
WHERE vizinhos >= $min_vizinhos AND den > 0
RETURN i.movieId AS movieId, i.title AS titulo, num / den AS score, vizinhos
ORDER BY score DESC, vizinhos DESC
LIMIT $n
"""


def prever(session, usuario, filme, k=K_VIZINHOS):
    linhas = session.run(Q_VIZINHOS_AVALIADOS, usuario=usuario, filme=filme, k=k).data()
    den = sum(abs(l["corr"]) for l in linhas)
    if den > 0:
        return sum(l["corr"] * l["nota"] for l in linhas) / den

    media = session.run(Q_MEDIA_FILME, filme=filme).single()
    if media and media["media"] is not None:
        return media["media"]
    media = session.run(Q_MEDIA_USUARIO, usuario=usuario).single()
    if media and media["media"] is not None:
        return media["media"]
    return 3.5


def recomendar(session, usuario, n=TOP_N, min_vizinhos=2):
    return session.run(Q_RECOMENDAR, usuario=usuario, n=n, min_vizinhos=min_vizinhos).data()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--usuario", type=int, required=True)
    parser.add_argument("--n", type=int, default=TOP_N)
    args = parser.parse_args()

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as s:
        recs = recomendar(s, args.usuario, args.n)
    driver.close()

    print(f"top {args.n} recomendacoes pro usuario {args.usuario}")
    for pos, r in enumerate(recs, start=1):
        print(f"{pos:2d}. {r['titulo']}  (nota prevista {r['score']:.2f}, {r['vizinhos']} vizinhos)")


if __name__ == "__main__":
    main()
