from app.config import (
    TOTAL_USUARIOS,
    TOTAL_PRODUCTOS,
    TOTAL_CATEGORIAS,
    TOTAL_EVENTOS,
    CASSANDRA_KEYSPACE,
)

from app.connections import (
    get_mongo_db,
    get_redis_client,
    get_neo4j_driver,
    get_cassandra_session,
)

from app.models.redis_keys import EVENT_COUNTER_KEY, TRENDING_GLOBAL_KEY


def check_result(label, expected, actual):
    """
    Compara un valor esperado contra un valor real
    y muestra el resultado por consola.
    """

    ok = expected == actual
    status = "OK" if ok else "ERROR"

    print(f"{label}: {status}")
    print(f"  esperado: {expected}")
    print(f"  actual:   {actual}")

    return ok


def check_positive(label, actual):
    """
    Valida que un valor sea mayor a cero.
    Sirve para estructuras derivadas donde no sabemos el total exacto,
    pero sí esperamos que existan datos.
    """

    ok = actual > 0
    status = "OK" if ok else "ERROR"

    print(f"{label}: {status}")
    print(f"  actual: {actual}")

    return ok


def validate_config():
    """
    Valida que la configuración del dataset lógico sea consistente.
    """

    total_logico = (
            TOTAL_USUARIOS
            + TOTAL_PRODUCTOS
            + TOTAL_CATEGORIAS
            + TOTAL_EVENTOS
    )

    print("Configuración del dataset")
    print("-" * 60)

    print(f"Usuarios configurados: {TOTAL_USUARIOS}")
    print(f"Productos configurados: {TOTAL_PRODUCTOS}")
    print(f"Categorías configuradas: {TOTAL_CATEGORIAS}")
    print(f"Eventos configurados: {TOTAL_EVENTOS}")
    print(f"Total lógico configurado: {total_logico}")

    return check_result(
        "Total lógico del dataset",
        1000,
        total_logico
    )


def validate_mongo():
    """
    Valida que MongoDB tenga cargados los documentos maestros:
    usuarios, productos y categorías.
    """

    client = None

    try:
        client, db = get_mongo_db()

        usuarios = db.usuarios.count_documents({})
        productos = db.productos.count_documents({})
        categorias = db.categorias.count_documents({})

        results = [
            check_result("MongoDB usuarios", TOTAL_USUARIOS, usuarios),
            check_result("MongoDB productos", TOTAL_PRODUCTOS, productos),
            check_result("MongoDB categorías", TOTAL_CATEGORIAS, categorias),
        ]

        return all(results)

    except Exception as error:
        print("MongoDB validación: ERROR")
        print(error)
        return False

    finally:
        if client:
            client.close()


def validate_redis():
    """
    Valida que Redis tenga cargados los datos derivados:
    contador de eventos y ranking global.
    """

    try:
        redis_client = get_redis_client()

        contador = redis_client.get(EVENT_COUNTER_KEY)
        contador = int(contador) if contador is not None else 0

        ranking_size = redis_client.zcard(TRENDING_GLOBAL_KEY)

        results = [
            check_result("Redis contador de eventos", TOTAL_EVENTOS, contador),
            check_positive("Redis ranking global con productos", ranking_size),
        ]

        return all(results)

    except Exception as error:
        print("Redis validación: ERROR")
        print(error)
        return False


def validate_cassandra():
    """
    Valida que Cassandra tenga cargados los eventos históricos
    en las tablas orientadas a consulta.
    """

    cluster = None

    try:
        cluster, session = get_cassandra_session()
        session.set_keyspace(CASSANDRA_KEYSPACE)

        # Para este TPI, con 750 eventos, COUNT(*) es aceptable.
        # En producción con millones de filas no sería una consulta recomendable.
        eventos_producto = session.execute(
            "SELECT COUNT(*) AS total FROM eventos_por_producto"
        ).one().total

        eventos_usuario = session.execute(
            "SELECT COUNT(*) AS total FROM eventos_por_usuario"
        ).one().total

        eventos_categoria = session.execute(
            "SELECT COUNT(*) AS total FROM eventos_por_categoria"
        ).one().total

        eventos_tipo = session.execute(
            "SELECT COUNT(*) AS total FROM eventos_por_tipo"
        ).one().total

        resumen_diario = session.execute(
            "SELECT COUNT(*) AS total FROM resumen_diario"
        ).one().total

        tendencias_categoria_fecha = session.execute(
            "SELECT COUNT(*) AS total FROM tendencias_por_categoria_fecha"
        ).one().total

        results = [
            check_result(
                "Cassandra eventos_por_producto",
                TOTAL_EVENTOS,
                eventos_producto
            ),
            check_result(
                "Cassandra eventos_por_usuario",
                TOTAL_EVENTOS,
                eventos_usuario
            ),
            check_result(
                "Cassandra eventos_por_categoria",
                TOTAL_EVENTOS,
                eventos_categoria
            ),
            check_result(
                "Cassandra eventos_por_tipo",
                TOTAL_EVENTOS,
                eventos_tipo
            ),
            check_positive(
                "Cassandra resumen_diario con filas",
                resumen_diario
            ),
            check_positive(
                "Cassandra tendencias_por_categoria_fecha con filas",
                tendencias_categoria_fecha
            ),
        ]

        return all(results)

    except Exception as error:
        print("Cassandra validación: ERROR")
        print(error)
        return False

    finally:
        if cluster:
            cluster.shutdown()


def validate_neo4j():
    """
    Valida que Neo4j tenga cargados los nodos principales
    y que las relaciones representen los eventos del dataset.
    """

    driver = None

    try:
        driver = get_neo4j_driver()

        with driver.session() as session:
            usuarios = session.run("""
                MATCH (u:Usuario)
                RETURN count(u) AS total
            """).single()["total"]

            productos = session.run("""
                MATCH (p:Producto)
                RETURN count(p) AS total
            """).single()["total"]

            categorias = session.run("""
                MATCH (c:Categoria)
                RETURN count(c) AS total
            """).single()["total"]

            eventos_representados = session.run("""
                MATCH (:Usuario)-[r]->(:Producto)
                WHERE type(r) IN ['VIO', 'CLICK', 'BUSCO', 'FAVORITO', 'COMPRO']
                RETURN coalesce(sum(r.cantidad), 0) AS total
            """).single()["total"]

        results = [
            check_result("Neo4j usuarios", TOTAL_USUARIOS, usuarios),
            check_result("Neo4j productos", TOTAL_PRODUCTOS, productos),
            check_result("Neo4j categorías", TOTAL_CATEGORIAS, categorias),
            check_result(
                "Neo4j eventos representados en relaciones",
                TOTAL_EVENTOS,
                eventos_representados
            ),
        ]

        return all(results)

    except Exception as error:
        print("Neo4j validación: ERROR")
        print(error)
        return False

    finally:
        if driver:
            driver.close()


def validate_all():
    """
    Ejecuta la validación completa del proyecto.
    """

    print("Validando coherencia general del proyecto...")
    print("=" * 60)

    results = []

    print("\nCONFIGURACIÓN")
    print("=" * 60)
    results.append(validate_config())

    print("\nMONGODB")
    print("=" * 60)
    results.append(validate_mongo())

    print("\nREDIS")
    print("=" * 60)
    results.append(validate_redis())

    print("\nCASSANDRA")
    print("=" * 60)
    results.append(validate_cassandra())

    print("\nNEO4J")
    print("=" * 60)
    results.append(validate_neo4j())

    print("\nRESULTADO GENERAL")
    print("=" * 60)

    if all(results):
        print("VALIDACIÓN GENERAL OK")
        print("Las bases cargadas son coherentes con el dataset configurado.")
    else:
        print("VALIDACIÓN GENERAL CON ERRORES")
        print("Revisar qué motor no coincide con los valores esperados.")