import argparse
from app.loaders.load_data import load_all
from app.queries.run_queries import run_all_queries
from app.generators.data_generator import generate_dataset, print_dataset_summary

from app.connections import (
    get_mongo_db,
    get_redis_client,
    get_neo4j_driver,
    get_cassandra_session,
)

from app.models.mongo_schema import setup_mongo
from app.models.cassandra_schema import setup_cassandra
from app.models.neo4j_schema import setup_neo4j
from app.models.redis_keys import setup_redis
from app.validation.validate_data import validate_all


def test_mongo():
    client = None

    try:
        client, db = get_mongo_db()
        db.command("ping")
        print("MongoDB OK")
    except Exception as error:
        print("MongoDB ERROR")
        print(error)
    finally:
        if client:
            client.close()


def test_redis():
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        print("Redis OK")
    except Exception as error:
        print("Redis ERROR")
        print(error)


def test_neo4j():
    driver = None

    try:
        driver = get_neo4j_driver()
        driver.verify_connectivity()
        print("Neo4j OK")
    except Exception as error:
        print("Neo4j ERROR")
        print(error)
    finally:
        if driver:
            driver.close()


def test_cassandra():
    cluster = None

    try:
        cluster, session = get_cassandra_session()
        row = session.execute("SELECT release_version FROM system.local").one()
        print(f"Cassandra OK - versión {row.release_version}")
    except Exception as error:
        print("Cassandra ERROR")
        print(error)
    finally:
        if cluster:
            cluster.shutdown()


def test_connections():
    print("Probando conexiones a las bases de datos...")
    print("-" * 50)

    test_mongo()
    test_redis()
    test_neo4j()
    test_cassandra()

    print("-" * 50)
    print("Prueba finalizada.")


def setup_all():
    print("Creando estructuras iniciales...")
    print("-" * 50)

    # MongoDB
    mongo_client = None
    try:
        mongo_client, mongo_db = get_mongo_db()
        setup_mongo(mongo_db)
    finally:
        if mongo_client:
            mongo_client.close()

    # Redis
    redis_client = get_redis_client()
    setup_redis(redis_client)

    # Neo4j
    neo4j_driver = None
    try:
        neo4j_driver = get_neo4j_driver()
        setup_neo4j(neo4j_driver)
    finally:
        if neo4j_driver:
            neo4j_driver.close()

    # Cassandra
    cassandra_cluster = None
    try:
        cassandra_cluster, cassandra_session = get_cassandra_session()
        setup_cassandra(cassandra_session)
    finally:
        if cassandra_cluster:
            cassandra_cluster.shutdown()

    print("-" * 50)
    print("Setup finalizado.")


def main():
    parser = argparse.ArgumentParser(
        description="Aplicación TPI - Detector de Tendencias"
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="test",
        choices=["test", "setup", "load", "queries", "generate", "validate"],
        help="Comando a ejecutar: test o setup"
    )

    args = parser.parse_args()

    if args.command == "test":
        test_connections()

    if args.command == "setup":
        setup_all()

    if args.command == "load":
        load_all()

    if args.command == "queries":
        run_all_queries()

    if args.command == "generate":
        dataset = generate_dataset()
        print_dataset_summary(dataset)

    if args.command == "validate":
        validate_all()

if __name__ == "__main__":
    main()