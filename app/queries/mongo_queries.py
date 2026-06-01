from app.connections import get_mongo_db
from app.config import (
    QUERY_LOW_STOCK_THRESHOLD,
    QUERY_SAMPLE_LIMIT,
    QUERY_TOP_LIMIT,
)


def query_counts(db):
    """
    Consulta 1:
    cuenta los documentos maestros guardados en MongoDB.

    Colecciones usadas:
    - usuarios
    - productos
    - categorias

    Esta consulta muestra el rol documental de MongoDB dentro del proyecto:
    guardar las entidades principales del catalogo y de los usuarios.
    """

    counts = {
        "usuarios": db.usuarios.count_documents({}),
        "productos": db.productos.count_documents({}),
        "categorias": db.categorias.count_documents({}),
    }

    return {
        "query": "count_documents",
        "descripcion": "Conteo de documentos maestros",
        "colecciones": ["usuarios", "productos", "categorias"],
        "counts": counts,
        "rows": [
            {
                "coleccion": collection,
                "total": total
            }
            for collection, total in counts.items()
        ]
    }


def query_productos_mayor_precio(db, limit=QUERY_TOP_LIMIT):
    """
    Consulta 2:
    obtiene los productos mas caros del catalogo.

    Coleccion usada:
    productos

    Funcionamiento:
    - find({}) toma todos los productos.
    - La proyeccion excluye _id y deja solo campos utiles.
    - sort("precio", -1) ordena de mayor a menor precio.
    - limit evita traer mas documentos de los necesarios.
    """

    rows = list(
        db.productos.find(
            {},
            {
                "_id": 0,
                "producto_id": 1,
                "nombre": 1,
                "precio": 1,
                "categoria_id": 1
            }
        ).sort("precio", -1).limit(limit)
    )

    return {
        "query": "productos.find().sort('precio', -1)",
        "descripcion": "Productos con mayor precio",
        "coleccion": "productos",
        "filtro": {},
        "orden": {
            "campo": "precio",
            "direccion": "desc"
        },
        "limit": limit,
        "rows": rows
    }


def query_stock_bajo(
    db,
    stock_maximo=QUERY_LOW_STOCK_THRESHOLD,
    limit=QUERY_SAMPLE_LIMIT,
):
    """
    Consulta 3:
    obtiene productos con bajo stock.

    Coleccion usada:
    productos

    Funcionamiento:
    - El filtro {"stock": {"$lt": stock_maximo}} busca productos con stock menor
      al umbral definido.
    - sort("stock", 1) ordena primero los productos mas criticos.
    - limit acota la muestra para consola y dashboard.
      Por defecto se muestran hasta 20 productos si existen.
    """

    rows = list(
        db.productos.find(
            {
                "stock": {"$lt": stock_maximo}
            },
            {
                "_id": 0,
                "producto_id": 1,
                "nombre": 1,
                "stock": 1
            }
        ).sort("stock", 1).limit(limit)
    )

    return {
        "query": "productos.find({'stock': {'$lt': stock_maximo}})",
        "descripcion": "Productos con stock bajo",
        "coleccion": "productos",
        "filtro": {
            "stock": {
                "$lt": stock_maximo
            }
        },
        "orden": {
            "campo": "stock",
            "direccion": "asc"
        },
        "limit": limit,
        "rows": rows
    }


def query_productos_por_categoria(db):
    """
    Consulta 4:
    cuenta productos agrupados por categoria y trae el nombre de la categoria.

    Colecciones usadas:
    - productos
    - categorias

    Funcionamiento del pipeline:
    - $group agrupa productos por categoria_id.
    - $lookup cruza cada categoria_id contra la coleccion categorias.
    - $unwind convierte el array del lookup en un documento simple.
    - $project arma la salida final compatible con el dashboard.
    - $sort ordena las categorias con mas productos primero.
    """

    pipeline = [
        {
            "$group": {
                "_id": "$categoria_id",
                "total": {"$sum": 1}
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
                "categoria_id": "$_id",
                "categoria": "$categoria_info.nombre",
                "total": 1
            }
        },
        {
            "$sort": {
                "total": -1
            }
        }
    ]

    rows = list(db.productos.aggregate(pipeline))

    return {
        "query": "productos.aggregate",
        "descripcion": "Cantidad de productos por categoria",
        "colecciones": ["productos", "categorias"],
        "pipeline": pipeline,
        "rows": rows
    }


def query_categoria_por_id(db, categoria_id):
    """
    Consulta 5:
    obtiene la informacion completa de una categoria por su identificador.

    Colecciones usadas:
    - categorias
    - productos

    Funcionamiento:
    - find_one busca la categoria que coincide con categoria_id.
    - La proyeccion excluye _id para devolver una estructura limpia.
    - count_documents cuenta cuantos productos pertenecen a esa categoria.
    - Esta consulta aprovecha el indice unico categoria_id definido en el setup.
    """

    row = db.categorias.find_one(
        {
            "categoria_id": categoria_id
        },
        {
            "_id": 0
        }
    )

    if row:
        row["total_productos"] = db.productos.count_documents({
            "categoria_id": categoria_id
        })

    return {
        "query": "categorias.find_one({'categoria_id': categoria_id})",
        "descripcion": "Informacion de categoria por ID",
        "colecciones": ["categorias", "productos"],
        "filtro": {
            "categoria_id": categoria_id
        },
        "rows": [row] if row else []
    }


def query_producto_por_id(db, producto_id):
    """
    Consulta 6:
    obtiene la informacion completa de un producto por su identificador.

    Coleccion usada:
    productos

    Funcionamiento:
    - find_one busca un unico documento que coincida con producto_id.
    - La proyeccion excluye _id para devolver una estructura mas limpia.
    - Esta consulta aprovecha el indice unico producto_id definido en el setup.
    """

    row = db.productos.find_one(
        {
            "producto_id": producto_id
        },
        {
            "_id": 0
        }
    )

    return {
        "query": "productos.find_one({'producto_id': producto_id})",
        "descripcion": "Informacion de producto por ID",
        "coleccion": "productos",
        "filtro": {
            "producto_id": producto_id
        },
        "rows": [row] if row else []
    }


def query_usuario_por_id(db, usuario_id):
    """
    Consulta 7:
    obtiene la informacion completa de un usuario por su identificador.

    Coleccion usada:
    usuarios

    Funcionamiento:
    - find_one busca un unico documento que coincida con usuario_id.
    - La proyeccion excluye _id para devolver una estructura mas limpia.
    - Esta consulta aprovecha el indice unico usuario_id definido en el setup.
    """

    row = db.usuarios.find_one(
        {
            "usuario_id": usuario_id
        },
        {
            "_id": 0
        }
    )

    return {
        "query": "usuarios.find_one({'usuario_id': usuario_id})",
        "descripcion": "Informacion de usuario por ID",
        "coleccion": "usuarios",
        "filtro": {
            "usuario_id": usuario_id
        },
        "rows": [row] if row else []
    }


def get_mongo_dashboard_data():
    """
    Devuelve datos MongoDB para el dashboard.

    Esta funcion no define las consultas en si mismas. Solo llama a las
    consultas especificas y adapta sus resultados al contrato definido en:
    docs/contrato-salidas-dashboard.md
    """

    client = None

    try:
        client, db = get_mongo_db()

        counts = query_counts(db)
        productos_por_categoria = query_productos_por_categoria(db)
        productos_mayor_precio = query_productos_mayor_precio(db)
        stock_bajo = query_stock_bajo(db)

        return {
            "status": "ok",
            "counts": counts["counts"],
            "productos_por_categoria": productos_por_categoria["rows"],
            "productos_mayor_precio": productos_mayor_precio["rows"],
            "stock_bajo": stock_bajo["rows"]
        }

    except Exception as error:
        return {
            "status": "error",
            "message": "Error al obtener datos de MongoDB para dashboard",
            "error": str(error),
            "counts": {
                "usuarios": 0,
                "productos": 0,
                "categorias": 0
            },
            "productos_por_categoria": [],
            "productos_mayor_precio": [],
            "stock_bajo": []
        }

    finally:
        if client:
            client.close()


def get_sample_value(db, collection_name, field_name):
    """
    Toma un valor real ya guardado para evitar IDs de demo hardcodeados.
    """

    document = db[collection_name].find_one(
        {
            field_name: {
                "$exists": True
            }
        },
        {
            "_id": 0,
            field_name: 1
        }
    )

    if not document:
        return None

    return document.get(field_name)


def run_mongo_queries():
    """
    Ejecuta las consultas MongoDB por consola.
    """

    client = None

    try:
        client, db = get_mongo_db()
        producto_id_demo = get_sample_value(db, "productos", "producto_id")
        usuario_id_demo = get_sample_value(db, "usuarios", "usuario_id")
        categoria_id_demo = get_sample_value(db, "categorias", "categoria_id")

        queries = [
            query_counts(db),
            query_productos_mayor_precio(db),
            query_stock_bajo(db),
            query_productos_por_categoria(db),
        ]

        if categoria_id_demo:
            queries.append(query_categoria_por_id(db, categoria_id_demo))

        if producto_id_demo:
            queries.append(query_producto_por_id(db, producto_id_demo))

        if usuario_id_demo:
            queries.append(query_usuario_por_id(db, usuario_id_demo))

        print("MongoDB queries")
        print("=" * 60)

        for query in queries:
            print()
            print(query["descripcion"])
            print("-" * 60)
            print(f"Consulta: {query['query']}")

            if "coleccion" in query:
                print(f"Coleccion: {query['coleccion']}")

            if "colecciones" in query:
                print(f"Colecciones: {', '.join(query['colecciones'])}")

            if "filtro" in query:
                print(f"Filtro: {query['filtro']}")

            if "orden" in query:
                print(f"Orden: {query['orden']}")

            if "limit" in query:
                print(f"Limite: {query['limit']}")

            if "pipeline" in query:
                print(f"Etapas del pipeline: {len(query['pipeline'])}")

            print(f"Filas devueltas: {len(query['rows'])}")

            for row in query["rows"]:
                print(row)

        return queries

    except Exception as error:
        print("MongoDB queries ERROR")
        print(error)
        return []

    finally:
        if client:
            client.close()
