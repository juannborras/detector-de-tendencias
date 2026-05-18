def setup_neo4j(driver):
    """
    Crea constraints e índices para Neo4j.

    Neo4j se usa para modelar relaciones:
    usuarios, productos, categorías y eventos de interacción.
    """

    queries = [
        """
        CREATE CONSTRAINT usuario_id_unique IF NOT EXISTS
        FOR (u:Usuario)
        REQUIRE u.usuario_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT producto_id_unique IF NOT EXISTS
        FOR (p:Producto)
        REQUIRE p.producto_id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT categoria_id_unique IF NOT EXISTS
        FOR (c:Categoria)
        REQUIRE c.categoria_id IS UNIQUE
        """,
        """
        CREATE INDEX usuario_nombre_index IF NOT EXISTS
            FOR (u:Usuario)
            ON (u.nombre)
        """,
        """
        CREATE INDEX producto_nombre_index IF NOT EXISTS
            FOR (p:Producto)
            ON (p.nombre)
        """
    ]

    with driver.session() as session:
        for query in queries:
            session.run(query)

    print("Neo4j setup OK")