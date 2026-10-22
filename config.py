import os

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j1234")

DATA_DIR = "data"
SEED = 42

K_VIZINHOS = 20
VIZINHOS_NO_GRAFO = 50
MIN_CO_AVALIACOES = 5

LIMIAR_RELEVANTE = 4.0
TOP_N = 10
