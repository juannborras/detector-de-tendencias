from app.config import CASSANDRA_KEYSPACE


def add_column_if_missing(session, table_name, column_name, column_type):
    """
    Agrega una columna a una tabla existente si todavia no esta creada.

    CREATE TABLE IF NOT EXISTS no modifica tablas ya existentes. Por eso,
    cuando agregamos una metrica nueva como total_favoritos, necesitamos
    intentar el ALTER TABLE para bases que ya fueron creadas previamente.
    """

    try:
        session.execute(
            f"ALTER TABLE {table_name} ADD {column_name} {column_type}"
        )
    except Exception as error:
        message = str(error).lower()
        expected_existing_column_error = (
            "already" in message
            or "duplicate" in message
            or "declared" in message
        )

        if not expected_existing_column_error:
            raise


def setup_cassandra(session):
    """
    Crea keyspace y tablas para Cassandra.

    Cassandra se usa para almacenar eventos históricos masivos.
    El diseño se hace según las consultas que queremos resolver.
    """

    session.execute(f"""
        CREATE KEYSPACE IF NOT EXISTS {CASSANDRA_KEYSPACE}
        WITH replication = {{
            'class': 'SimpleStrategy',
            'replication_factor': 1
        }}
    """)

    session.set_keyspace(CASSANDRA_KEYSPACE)

    session.execute("""
                    CREATE TABLE IF NOT EXISTS eventos_por_producto (
                                                                        producto_id text,
                                                                        fecha date,
                                                                        timestamp timestamp,
                                                                        evento_id text,
                                                                        usuario_id text,
                                                                        tipo_evento text,
                                                                        categoria_id text,
                                                                        PRIMARY KEY ((producto_id, fecha), timestamp, evento_id)
                        ) WITH CLUSTERING ORDER BY (timestamp DESC)
                    """)

    session.execute("""
                    CREATE TABLE IF NOT EXISTS eventos_por_usuario (
                                                                       usuario_id text,
                                                                       fecha date,
                                                                       timestamp timestamp,
                                                                       evento_id text,
                                                                       producto_id text,
                                                                       tipo_evento text,
                                                                       categoria_id text,
                                                                       PRIMARY KEY ((usuario_id, fecha), timestamp, evento_id)
                        ) WITH CLUSTERING ORDER BY (timestamp DESC)
                    """)

    session.execute("""
                    CREATE TABLE IF NOT EXISTS eventos_por_categoria (
                                                                         categoria_id text,
                                                                         fecha date,
                                                                         timestamp timestamp,
                                                                         evento_id text,
                                                                         usuario_id text,
                                                                         producto_id text,
                                                                         tipo_evento text,
                                                                         PRIMARY KEY ((categoria_id, fecha), timestamp, evento_id)
                        ) WITH CLUSTERING ORDER BY (timestamp DESC)
                    """)

    session.execute("""
                    CREATE TABLE IF NOT EXISTS resumen_diario (
                                                                  fecha date,
                                                                  producto_id text,
                                                                  categoria_id text,
                                                                  total_eventos int,
                                                                  total_vistas int,
                                                                  total_clicks int,
                                                                  total_busquedas int,
                                                                  total_favoritos int,
                                                                  total_compras int,
                                                                  score_tendencia double,
                                                                  PRIMARY KEY ((fecha), producto_id)
                        )
                    """)

    session.execute("""
                    CREATE TABLE IF NOT EXISTS eventos_por_tipo (
                                                                    tipo_evento text,
                                                                    fecha date,
                                                                    timestamp timestamp,
                                                                    evento_id text,
                                                                    usuario_id text,
                                                                    producto_id text,
                                                                    categoria_id text,
                                                                    PRIMARY KEY ((tipo_evento, fecha), timestamp, evento_id)
                        ) WITH CLUSTERING ORDER BY (timestamp DESC)
                    """)

    session.execute("""
                CREATE TABLE IF NOT EXISTS tendencias_por_categoria_fecha (
                                                                              categoria_id text,
                                                                              fecha date,
                                                                              score_tendencia double,
                                                                              producto_id text,
                                                                              total_eventos int,
                                                                              total_vistas int,
                                                                              total_clicks int,
                                                                              total_busquedas int,
                                                                              total_favoritos int,
                                                                              total_compras int,
                                                                              PRIMARY KEY ((categoria_id, fecha), score_tendencia, producto_id)
                    ) WITH CLUSTERING ORDER BY (score_tendencia DESC)
                """)

    add_column_if_missing(
        session,
        "resumen_diario",
        "total_favoritos",
        "int"
    )

    add_column_if_missing(
        session,
        "tendencias_por_categoria_fecha",
        "total_favoritos",
        "int"
    )

    print("Cassandra setup OK")
