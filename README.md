# Sistema de recomendação de filmes com grafo (MovieLens + Neo4j)

Trabalho de recomendação usando o MovieLens (`ml-latest-small`), só com `ratings.csv` e `movies.csv`. Montei um grafo no Neo4j, calculei a correlação de Pearson entre filmes, guardei isso no próprio grafo e fiz a recomendação com KNN. No final separei 80/20 e medi precisão e recall.

A única biblioteca externa é o driver do Neo4j (`neo4j`). O resto é Python puro (`csv`, `math`, `random`, `argparse`). Nada de pandas, numpy ou sklearn.

## Como rodar

1. Baixar o `ml-latest-small` em https://grouplens.org/datasets/movielens/ e colocar `ratings.csv` e `movies.csv` dentro de uma pasta `data/`.
2. Subir um Neo4j local (5.x) e ajustar usuário/senha. Por padrão uso `neo4j` / `neo4j1234` em `bolt://localhost:7687`. Dá pra mudar com as variáveis de ambiente `NEO4J_URI`, `NEO4J_USER` e `NEO4J_PASSWORD`.
3. `pip install -r requirements.txt`
4. Rodar na ordem:

```
python dividir.py
python inserir.py
python similaridade.py
python consultas.py --usuario 1
python avaliar.py
```

Também dá pra pedir só as recomendações de alguém: `python recomendar.py --usuario 1 --n 10`.

O `similaridade.py` é o mais demorado (alguns minutos), porque calcula a correlação de todos os filmes contra todos que têm usuários em comum.

## O que cada arquivo faz

- `config.py`: conexão com o Neo4j e parâmetros (K, limiar, top N, seed).
- `dividir.py`: embaralha o `ratings.csv` e separa 80% em `train.csv` e 20% em `test.csv`.
- `inserir.py`: cria os nós e as arestas no Neo4j.
- `similaridade.py`: calcula Pearson entre filmes e grava as arestas `SIMILAR`.
- `recomendar.py`: previsão de nota (KNN) e top recomendações pra um usuário.
- `consultas.py`: consultas e agregações no grafo.
- `avaliar.py`: avaliação no conjunto de teste.

## Modelagem do grafo

**Nós**

| Nó | Atributos |
|---|---|
| `User` | `userId`, `avgRating`, `numRatings` |
| `Movie` | `movieId`, `title`, `year`, `avgRating`, `numRatings` |
| `Genre` | `name` |

**Arestas**

| Aresta | Atributos |
|---|---|
| `(User)-[:RATED]->(Movie)` | `rating`, `timestamp` |
| `(Movie)-[:HAS_GENRE]->(Genre)` | nenhum |
| `(Movie)-[:SIMILAR]->(Movie)` | `corr` (Pearson), `coRaters` (quantos usuários avaliaram os dois) |

Decisões que tomei:

- Gênero virou nó em vez de string no filme. Assim a consulta "comédias que o usuário gostou" é só caminhar pelo grafo, e dá pra agrupar por gênero fácil.
- O ano é extraído do título (o `movies.csv` traz algo tipo `Toy Story (1995)`).
- Filmes com `(no genres listed)` ficam sem aresta de gênero.
- Só as avaliações de **treino** entram no grafo. As de teste ficam fora, senão o modelo veria a resposta. As médias (`avgRating`) também são calculadas só com o treino.
- Pra não guardar todos os pares de filmes (seriam milhões de arestas), cada filme guarda só os 50 vizinhos com maior |correlação|, e só pares com pelo menos 5 usuários em comum (senão sai correlação 1 ou -1 por acaso com 2 ou 3 notas).

## Similaridade (Pearson entre filmes)

Como cada usuário avalia poucos filmes, comparei filmes em vez de usuários. Pra dois filmes i e j:

```
c(i,j) = soma_k (r_i^k - media_i)(r_j^k - media_j)
         ---------------------------------------------------
         raiz(soma_k (r_i^k - media_i)^2) * raiz(soma_k (r_j^k - media_j)^2)
```

O `k` percorre só os usuários que avaliaram os dois filmes, e `media_i` é a nota média do filme i (calculada no treino). Pra não fazer todos os pares ingenuamente, o script percorre, pra cada filme, os usuários que o avaliaram e acumula os termos dos outros filmes desses usuários. O resultado vira aresta `SIMILAR` no grafo.

## Regressão com KNN

Pra prever a nota que o usuário `u` daria pro filme `i`, pego os `K` filmes mais similares a `i` (pelo maior |corr|) que o usuário `u` já avaliou, e faço a média ponderada:

```
nota_prevista(u,i) = soma_{j em N} c(i,j) * r_u^j  /  soma_{j em N} |c(i,j)|
```

onde `N` são esses K vizinhos e `r_u^j` é a nota que `u` deu pro vizinho `j`. Usei `K = 20`. Isso é feito com uma query Cypher que caminha `Movie -SIMILAR-> Movie <-RATED- User`.

Se o filme não tem nenhum vizinho avaliado pelo usuário, caio na média do filme, depois na média do usuário, e por último em 3.5.

## Top recomendações

Pro usuário X, a query pega todos os filmes que ele avaliou, olha os filmes similares a eles que ele ainda não viu e calcula a mesma média ponderada. Filmes com menos de 2 vizinhos em comum com o histórico do usuário são descartados. Ordena pela nota prevista e devolve os top N.

## Consultas (`consultas.py`)

1. Quantas comédias o usuário X assistiu e deu nota 4 ou mais (a do enunciado), com exemplos.
2. Gêneros preferidos do usuário (média de notas por gênero).
3. Filmes mais parecidos com um filme (`--filme`).
4. Filmes mais bem avaliados com pelo menos 50 avaliações.
5. Top recomendações pro usuário X.

Exemplo: `python consultas.py --usuario 1 --filme 1 --n 10`

## Avaliação

Divisão aleatória 80% treino / 20% teste (seed 42). Pra cada usuário do teste:

- Considero **relevante** todo filme que ele avaliou com nota >= 4 no conjunto de teste.
- Gero o top 10 de recomendações usando só o grafo de treino (que já exclui o que ele viu no treino).
- `acertos` = quantos do top 10 estão entre os relevantes.
- `precisão@10 = acertos / 10` e `recall@10 = acertos / total de relevantes do usuário`.

O resultado final é a média entre os usuários que têm pelo menos um filme relevante no teste. Também calculei MAE e RMSE da previsão de nota em todas as avaliações de teste, só pra ver como a regressão se comporta além do ranking.

### Resultados

Preencher depois de rodar o `avaliar.py`:

```
precisao@10:
recall@10:
MAE:
RMSE:
```

## Limitações

- A divisão é aleatória por avaliação, não por tempo. Pode vazar um pouco de informação "do futuro" pro treino.
- Filmes que só aparecem no teste (ou com poucas notas no treino) não têm vizinhos, então não são recomendados e a previsão deles cai na média.
- Recomendação por similaridade de item tende a favorecer filmes populares, então a precisão fica baixa em valor absoluto, que é esperado nesse tipo de métrica com muitos filmes e poucas notas por usuário.
