def get_mongo_dashboard_data():
    """
    Devuelve datos de MongoDB para el dashboard.

    Estado actual: placeholder.
    El responsable de MongoDB debe reemplazar esta función
    por consultas reales a MongoDB.
    """

    return {
        "status": "pending",
        "message": "MongoDB dashboard data pendiente de implementación",
        "counts": {
            "usuarios": 0,
            "productos": 0,
            "categorias": 0
        },
        "productos_por_categoria": [],
        "productos_mayor_precio": [],
        "stock_bajo": []
    }


def run_mongo_queries():
    """
    Ejecuta consultas MongoDB por consola.
    """

    data = get_mongo_dashboard_data()

    print("MongoDB queries")
    print("-" * 50)
    print(data)

    return data