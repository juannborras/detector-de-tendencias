def get_redis_dashboard_data():
    """
    Devuelve datos de Redis para el dashboard.

    Estado actual: placeholder.
    El responsable de Redis debe reemplazar esta función
    por consultas reales a Redis.
    """

    return {
        "status": "pending",
        "message": "Redis dashboard data pendiente de implementación",
        "contador_eventos": 0,
        "top_global": [],
        "top_por_categoria": {},
        "cache_top10_global": [],
        "sesiones_sample": []
    }


def run_redis_queries():
    """
    Ejecuta consultas Redis por consola.
    """

    data = get_redis_dashboard_data()

    print("Redis queries")
    print("-" * 50)
    print(data)

    return data