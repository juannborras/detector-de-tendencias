def get_neo4j_dashboard_data():
    """
    Devuelve datos de Neo4j para el dashboard.

    Estado actual: placeholder.
    El responsable de Neo4j debe reemplazar esta función
    por consultas reales a Neo4j.
    """

    return {
        "status": "pending",
        "message": "Neo4j dashboard data pendiente de implementación",
        "counts": {
            "usuarios": 0,
            "productos": 0,
            "categorias": 0,
            "relaciones_interaccion": 0,
            "eventos_representados": 0
        },
        "relaciones_por_tipo": [],
        "usuarios_mas_activos": [],
        "productos_mas_conectados": [],
        "recomendaciones_sample": []
    }


def run_neo4j_queries():
    """
    Ejecuta consultas Neo4j por consola.
    """

    data = get_neo4j_dashboard_data()

    print("Neo4j queries")
    print("-" * 50)
    print(data)

    return data