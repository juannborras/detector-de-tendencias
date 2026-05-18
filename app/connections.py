from pymongo import MongoClient
from redis import Redis
from neo4j import GraphDatabase
from cassandra.cluster import Cluster

from app.config import (
    MONGO_URI,
    MONGO_DB,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    CASSANDRA_HOST,
    CASSANDRA_PORT,
)

def get_mongo_db():
    """
    Crea una conexión a MongoDB y devuelve la base de datos del proyecto.
    """
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    return client, db


def get_redis_client():
    """
    Crea una conexión a Redis.
    """
    redis_client = Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True
    )
    return redis_client


def get_neo4j_driver():
    """
    Crea una conexión a Neo4j usando el protocolo Bolt.
    """
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )
    return driver


def get_cassandra_session():
    """
    Crea una conexión a Cassandra.
    """
    cluster = Cluster(
        [CASSANDRA_HOST],
        port=CASSANDRA_PORT
    )
    session = cluster.connect()
    return cluster, session