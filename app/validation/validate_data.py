from app.config import (
    TOTAL_USUARIOS,
    TOTAL_PRODUCTOS,
    TOTAL_CATEGORIAS,
    TOTAL_EVENTOS,
    CASSANDRA_KEYSPACE,
    EXPECTED_TOTAL_REGISTROS,
    MIN_PRODUCTOS_POR_CATEGORIA,
)

from app.connections import (
    get_mongo_db,
    get_redis_client,
    get_neo4j_driver,
    get_cassandra_session,
)

from app.models.redis_keys import EVENT_COUNTER_KEY, TRENDING_GLOBAL_KEY
from app.generators.data_generator import (
    PRODUCT_BASE_NAMES_BY_CATEGORY_ID,
    PRODUCT_BRANDS_BY_CATEGORY_ID,
)


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


def check_minimum(label, minimum, actual):
    """
    Valida que un valor sea mayor o igual a un minimo esperado.
    Sirve para reglas de distribucion, como productos por categoria.
    """

    ok = actual >= minimum
    status = "OK" if ok else "ERROR"

    print(f"{label}: {status}")
    print(f"  minimo: {minimum}")
    print(f"  actual: {actual}")

    return ok


def product_matches_category(product):
    """
    Valida que el nombre base del producto corresponda a su categoria.
    """

    allowed_names = PRODUCT_BASE_NAMES_BY_CATEGORY_ID.get(
        product.get("categoria_id"),
        [],
    )

    return any(
        product.get("nombre", "").startswith(f"{name} ")
        for name in allowed_names
    )


def brand_matches_category(product):
    """
    Valida que la marca del producto corresponda a su categoria.
    """

    allowed_brands = PRODUCT_BRANDS_BY_CATEGORY_ID.get(
        product.get("categoria_id"),
        [],
    )

    return product.get("marca") in allowed_brands


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
    print(f"Minimo productos por categoria: {MIN_PRODUCTOS_POR_CATEGORIA}")
    print(f"Eventos configurados: {TOTAL_EVENTOS}")
    print(f"Total lógico configurado: {total_logico}")

    minimum_required_products = TOTAL_CATEGORIAS * MIN_PRODUCTOS_POR_CATEGORIA

    results = [
        check_result(
            "Total lógico del dataset",
            EXPECTED_TOTAL_REGISTROS,
            total_logico
        ),
        check_minimum(
            "Productos suficientes para cubrir categorias",
            minimum_required_products,
            TOTAL_PRODUCTOS
        )
    ]

    return all(results)


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
        productos_documentos = list(
            db.productos.find(
                {},
                {
                    "_id": 0,
                    "producto_id": 1,
                    "nombre": 1,
                    "marca": 1,
                    "categoria_id": 1,
                }
            )
        )
        productos_por_categoria = list(
            db.categorias.aggregate([
                {
                    "$lookup": {
                        "from": "productos",
                        "localField": "categoria_id",
                        "foreignField": "categoria_id",
                        "as": "productos"
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "categoria_id": 1,
                        "nombre": 1,
                        "total_productos": {"$size": "$productos"}
                    }
                }
            ])
        )

        minimo_real = min(
            (categoria["total_productos"] for categoria in productos_por_categoria),
            default=0
        )

        categorias_insuficientes = [
            categoria
            for categoria in productos_por_categoria
            if categoria["total_productos"] < MIN_PRODUCTOS_POR_CATEGORIA
        ]
        productos_incoherentes = [
            producto
            for producto in productos_documentos
            if not product_matches_category(producto)
        ]
        marcas_incoherentes = [
            producto
            for producto in productos_documentos
            if not brand_matches_category(producto)
        ]

        results = [
            check_result("MongoDB usuarios", TOTAL_USUARIOS, usuarios),
            check_result("MongoDB productos", TOTAL_PRODUCTOS, productos),
            check_result("MongoDB categorías", TOTAL_CATEGORIAS, categorias),
            check_minimum(
                "MongoDB productos por categoria",
                MIN_PRODUCTOS_POR_CATEGORIA,
                minimo_real
            ),
            check_result(
                "MongoDB productos coherentes con categoria",
                0,
                len(productos_incoherentes)
            ),
            check_result(
                "MongoDB marcas coherentes con categoria",
                0,
                len(marcas_incoherentes)
            ),
        ]

        if categorias_insuficientes:
            print("Categorias con menos productos de los esperados:")
            for categoria in categorias_insuficientes:
                print(
                    f"  {categoria['categoria_id']} - "
                    f"{categoria['nombre']}: {categoria['total_productos']}"
                )

        if productos_incoherentes:
            print("Productos con categoria incoherente:")
            for producto in productos_incoherentes[:10]:
                print(
                    f"  {producto['producto_id']} - "
                    f"{producto['nombre']} - "
                    f"{producto['categoria_id']}"
                )

        if marcas_incoherentes:
            print("Productos con marca incoherente:")
            for producto in marcas_incoherentes[:10]:
                print(
                    f"  {producto['producto_id']} - "
                    f"{producto['nombre']} - "
                    f"{producto['marca']} - "
                    f"{producto['categoria_id']}"
                )

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

        # Para este TPI, con 1250 eventos, COUNT(*) es aceptable.
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
