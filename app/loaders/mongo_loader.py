from app.config import LOAD_MODE
from app.connections import get_mongo_db


def load_mongo(dataset):
    """
    Carga usuarios, productos y categorías en MongoDB.

    MongoDB funciona como base documental maestra:
    - usuarios
    - productos
    - categorías
    """

    client = None

    try:
        client, db = get_mongo_db()

        usuarios = dataset["usuarios"]
        productos = dataset["productos"]
        categorias = dataset["categorias"]

        if LOAD_MODE == "reset":
            db.usuarios.delete_many({})
            db.productos.delete_many({})
            db.categorias.delete_many({})

        for usuario in usuarios:
            db.usuarios.update_one(
                {"usuario_id": usuario["usuario_id"]},
                {"$set": usuario},
                upsert=True
            )

        for producto in productos:
            db.productos.update_one(
                {"producto_id": producto["producto_id"]},
                {"$set": producto},
                upsert=True
            )

        for categoria in categorias:
            db.categorias.update_one(
                {"categoria_id": categoria["categoria_id"]},
                {"$set": categoria},
                upsert=True
            )

        print(f"MongoDB: {len(usuarios)} usuarios cargados")
        print(f"MongoDB: {len(productos)} productos cargados")
        print(f"MongoDB: {len(categorias)} categorías cargadas")

    finally:
        if client:
            client.close()