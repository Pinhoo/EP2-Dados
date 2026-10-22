import argparse

from neo4j import GraphDatabase

from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, TOP_N
from recomendar import recomendar


def comedias_nota_alta(s, usuario, minimo=4.0):
    total = s.run(
        """
        MATCH (u:User {userId: $usuario})-[r:RATED]->(m:Movie)-[:HAS_GENRE]->(:Genre {name: 'Comedy'})
        WHERE r.rating >= $minimo
        RETURN count(m) AS total
        """,
        usuario=usuario,
        minimo=minimo,
    ).single()["total"]
    print(f"\n[1] comedias que o usuario {usuario} avaliou com nota >= {minimo}: {total}")

    exemplos = s.run(
        """
        MATCH (u:User {userId: $usuario})-[r:RATED]->(m:Movie)-[:HAS_GENRE]->(:Genre {name: 'Comedy'})
        WHERE r.rating >= $minimo
        RETURN m.title AS titulo, r.rating AS nota
        ORDER BY r.rating DESC, m.title
        LIMIT 10
        """,
        usuario=usuario,
        minimo=minimo,
    ).data()
    for e in exemplos:
        print(f"    {e['nota']:.1f}  {e['titulo']}")


def generos_favoritos(s, usuario):
    print(f"\n[2] generos preferidos do usuario {usuario} (min. 5 filmes)")
    linhas = s.run(
        """
        MATCH (u:User {userId: $usuario})-[r:RATED]->(:Movie)-[:HAS_GENRE]->(g:Genre)
        WITH g.name AS genero, avg(r.rating) AS media, count(*) AS qtd
        WHERE qtd >= 5
        RETURN genero, media, qtd
        ORDER BY media DESC
        LIMIT 5
        """,
        usuario=usuario,
    ).data()
    for l in linhas:
        print(f"    {l['genero']}: media {l['media']:.2f} em {l['qtd']} filmes")


def mais_parecidos(s, filme):
    titulo = s.run("MATCH (m:Movie {movieId: $f}) RETURN m.title AS t", f=filme).single()
    nome = titulo["t"] if titulo else str(filme)
    print(f"\n[3] filmes mais parecidos com {nome}")
    linhas = s.run(
        """
        MATCH (:Movie {movieId: $f})-[s:SIMILAR]->(j:Movie)
        WHERE s.corr > 0
        RETURN j.title AS titulo, s.corr AS corr, s.coRaters AS n
        ORDER BY s.corr DESC
        LIMIT 5
        """,
        f=filme,
    ).data()
    for l in linhas:
        print(f"    {l['corr']:.3f} ({l['n']} usuarios em comum)  {l['titulo']}")


def melhores_filmes(s):
    print("\n[4] filmes mais bem avaliados (min. 50 avaliacoes no treino)")
    linhas = s.run(
        """
        MATCH (m:Movie)
        WHERE m.numRatings >= 50
        RETURN m.title AS titulo, m.avgRating AS media, m.numRatings AS qtd
        ORDER BY media DESC
        LIMIT 5
        """
    ).data()
    for l in linhas:
        print(f"    {l['media']:.2f} ({l['qtd']} avaliacoes)  {l['titulo']}")


def top_recomendacoes(s, usuario, n):
    print(f"\n[5] top {n} recomendacoes para o usuario {usuario}")
    for pos, r in enumerate(recomendar(s, usuario, n), start=1):
        print(f"    {pos:2d}. {r['titulo']}  (nota prevista {r['score']:.2f})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--usuario", type=int, default=1)
    parser.add_argument("--filme", type=int, default=1)
    parser.add_argument("--n", type=int, default=TOP_N)
    args = parser.parse_args()

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as s:
        comedias_nota_alta(s, args.usuario)
        generos_favoritos(s, args.usuario)
        mais_parecidos(s, args.filme)
        melhores_filmes(s)
        top_recomendacoes(s, args.usuario, args.n)
    driver.close()


if __name__ == "__main__":
    main()
