from collections import defaultdict
from datetime import datetime

from app.config import LOAD_MODE, CASSANDRA_KEYSPACE
from app.connections import get_cassandra_session


EVENT_SCORE = {
    "vista": 1,
    "click": 2,
    "busqueda": 3,
    "favorito": 4,
    "compra": 5,
}


def load_cassandra(dataset):
    """
    Carga eventos históricos en Cassandra.

    Un mismo evento lógico se replica en varias tablas porque
    Cassandra se modela según las consultas que se necesitan resolver.
    """

    cluster = None

    try:
        cluster, session = get_cassandra_session()
        session.set_keyspace(CASSANDRA_KEYSPACE)

        eventos = dataset["eventos"]

        if LOAD_MODE == "reset":
            tables = [
                "eventos_por_producto",
                "eventos_por_usuario",
                "eventos_por_categoria",
                "eventos_por_tipo",
                "resumen_diario",
                "tendencias_por_categoria_fecha",
            ]

            for table in tables:
                session.execute(f"TRUNCATE {table}")

        insert_producto = session.prepare("""
                                          INSERT INTO eventos_por_producto (
                                              producto_id, fecha, timestamp, evento_id,
                                              usuario_id, tipo_evento, categoria_id
                                          )
                                          VALUES (?, ?, ?, ?, ?, ?, ?)
                                          """)

        insert_usuario = session.prepare("""
                                         INSERT INTO eventos_por_usuario (
                                             usuario_id, fecha, timestamp, evento_id,
                                             producto_id, tipo_evento, categoria_id
                                         )
                                         VALUES (?, ?, ?, ?, ?, ?, ?)
                                         """)

        insert_categoria = session.prepare("""
                                           INSERT INTO eventos_por_categoria (
                                               categoria_id, fecha, timestamp, evento_id,
                                               usuario_id, producto_id, tipo_evento
                                           )
                                           VALUES (?, ?, ?, ?, ?, ?, ?)
                                           """)

        insert_tipo = session.prepare("""
                                      INSERT INTO eventos_por_tipo (
                                          tipo_evento, fecha, timestamp, evento_id,
                                          usuario_id, producto_id, categoria_id
                                      )
                                      VALUES (?, ?, ?, ?, ?, ?, ?)
                                      """)

        resumen = defaultdict(lambda: {
            "total_eventos": 0,
            "total_vistas": 0,
            "total_clicks": 0,
            "total_busquedas": 0,
            "total_compras": 0,
            "score_tendencia": 0.0,
            "categoria_id": None,
        })

        for evento in eventos:
            ts = datetime.fromisoformat(evento["timestamp"])
            fecha = ts.date()

            producto_id = evento["producto_id"]
            usuario_id = evento["usuario_id"]
            categoria_id = evento["categoria_id"]
            tipo_evento = evento["tipo_evento"]
            evento_id = evento["evento_id"]

            session.execute(insert_producto, (
                producto_id,
                fecha,
                ts,
                evento_id,
                usuario_id,
                tipo_evento,
                categoria_id,
            ))

            session.execute(insert_usuario, (
                usuario_id,
                fecha,
                ts,
                evento_id,
                producto_id,
                tipo_evento,
                categoria_id,
            ))

            session.execute(insert_categoria, (
                categoria_id,
                fecha,
                ts,
                evento_id,
                usuario_id,
                producto_id,
                tipo_evento,
            ))

            session.execute(insert_tipo, (
                tipo_evento,
                fecha,
                ts,
                evento_id,
                usuario_id,
                producto_id,
                categoria_id,
            ))

            key = (fecha, producto_id)
            resumen[key]["categoria_id"] = categoria_id
            resumen[key]["total_eventos"] += 1
            resumen[key]["score_tendencia"] += EVENT_SCORE.get(tipo_evento, 0)

            if tipo_evento == "vista":
                resumen[key]["total_vistas"] += 1
            elif tipo_evento == "click":
                resumen[key]["total_clicks"] += 1
            elif tipo_evento == "busqueda":
                resumen[key]["total_busquedas"] += 1
            elif tipo_evento == "compra":
                resumen[key]["total_compras"] += 1

        insert_resumen = session.prepare("""
                                         INSERT INTO resumen_diario (
                                             fecha, producto_id, categoria_id, total_eventos,
                                             total_vistas, total_clicks, total_busquedas,
                                             total_compras, score_tendencia
                                         )
                                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                         """)

        insert_tendencia_categoria = session.prepare("""
                                                     INSERT INTO tendencias_por_categoria_fecha (
                                                         categoria_id, fecha, score_tendencia, producto_id,
                                                         total_eventos, total_vistas, total_clicks,
                                                         total_busquedas, total_compras
                                                     )
                                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                                     """)

        for (fecha, producto_id), data in resumen.items():
            session.execute(insert_resumen, (
                fecha,
                producto_id,
                data["categoria_id"],
                data["total_eventos"],
                data["total_vistas"],
                data["total_clicks"],
                data["total_busquedas"],
                data["total_compras"],
                float(data["score_tendencia"]),
            ))

            session.execute(insert_tendencia_categoria, (
                data["categoria_id"],
                fecha,
                float(data["score_tendencia"]),
                producto_id,
                data["total_eventos"],
                data["total_vistas"],
                data["total_clicks"],
                data["total_busquedas"],
                data["total_compras"],
            ))

        print(f"Cassandra: {len(eventos)} eventos lógicos cargados")
        print(f"Cassandra: {len(resumen)} resúmenes diarios generados")

    finally:
        if cluster:
            cluster.shutdown()