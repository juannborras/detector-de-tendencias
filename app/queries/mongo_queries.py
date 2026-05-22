from app.connections import get_mongo_db


def get_mongo_dashboard_data():
    """
    Devuelve datos reales de MongoDB para el dashboard.
    """

    client = None

    try:
        client, db = get_mongo_db()

        # Conteos generales
        total_usuarios = db.usuarios.count_documents({})
        total_productos = db.productos.count_documents({})
        total_categorias = db.categorias.count_documents({})

        # Productos más caros
        productos_mayor_precio = list(
            db.productos.find(
                {},
                {
                    "_id": 0,
                    "producto_id": 1,
                    "nombre": 1,
                    "precio": 1,
                    "categoria_id": 1
                }
            ).sort("precio", -1).limit(5)
        )

        # Productos con stock bajo
        stock_bajo = list(
            db.productos.find(
                {
                    "stock": {"$lt": 10}
                },
                {
                    "_id": 0,
                    "producto_id": 1,
                    "nombre": 1,
                    "stock": 1
                }
            ).limit(10)
        )

        # Productos por categoría con nombre real
        productos_por_categoria = list(
            db.productos.aggregate([
                {
                    "$group": {
                        "_id": "$categoria_id",
                        "cantidad_productos": {"$sum": 1}
                    }
                },

                {
                    "$lookup": {
                        "from": "categorias",
                        "localField": "_id",
                        "foreignField": "categoria_id",
                        "as": "categoria_info"
                    }
                },

                {
                    "$unwind": "$categoria_info"
                },

                {
                    "$project": {
                        "_id": 0,
                        "categoria": "$categoria_info.nombre",
                        "cantidad_productos": 1
                    }
                },

                {
                    "$sort": {
                        "cantidad_productos": -1
                    }
                }
            ])
        )

        return {
            "status": "ok",

            "counts": {
                "usuarios": total_usuarios,
                "productos": total_productos,
                "categorias": total_categorias
            },

            "productos_por_categoria": productos_por_categoria,

            "productos_mayor_precio": productos_mayor_precio,

            "stock_bajo": stock_bajo
        }

    finally:
        if client:
            client.close()


def run_mongo_queries():
    """
    Ejecuta consultas MongoDB por consola.
    """

    data = get_mongo_dashboard_data()

    print("MongoDB queries")
    print("-" * 50)

    print("\nConteos generales")
    print(f"Usuarios: {data['counts']['usuarios']}")
    print(f"Productos: {data['counts']['productos']}")
    print(f"Categorías: {data['counts']['categorias']}")

    print("\nTop productos más caros")
    for producto in data["productos_mayor_precio"]:
        print(producto)

    print("\nProductos con stock bajo")
    for producto in data["stock_bajo"]:
        print(producto)

    print("\nProductos por categoría")
    for categoria in data["productos_por_categoria"]:
        print(categoria)

    return data