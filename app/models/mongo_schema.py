from pymongo.errors import CollectionInvalid


def setup_mongo(db):
    """
    Crea colecciones e índices para MongoDB.

    MongoDB se usa para guardar datos documentales:
    - productos
    - usuarios
    - categorías
    """

    collections = db.list_collection_names()

    if "productos" not in collections:
        try:
            db.create_collection("productos")
        except CollectionInvalid:
            pass

    if "usuarios" not in collections:
        try:
            db.create_collection("usuarios")
        except CollectionInvalid:
            pass

    if "categorias" not in collections:
        try:
            db.create_collection("categorias")
        except CollectionInvalid:
            pass

    # Índices de productos
    db.productos.create_index("producto_id", unique=True)
    db.productos.create_index("categoria_id")
    db.productos.create_index("nombre")

    # Índices de usuarios
    db.usuarios.create_index("usuario_id", unique=True)
    db.usuarios.create_index("email", unique=True)

    # Índices de categorías
    db.categorias.create_index("categoria_id", unique=True)
    db.categorias.create_index("nombre", unique=True)

    print("MongoDB setup OK")