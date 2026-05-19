from app.config import LOAD_MODE
from app.connections import get_neo4j_driver


RELATION_BY_EVENT_TYPE = {
    "vista": "VIO",
    "click": "CLICK",
    "busqueda": "BUSCO",
    "favorito": "FAVORITO",
    "compra": "COMPRO",
}


def load_neo4j(dataset):
    """
    Carga nodos y relaciones en Neo4j.

    Neo4j representa:
    - usuarios
    - productos
    - categorías
    - relaciones de interacción usuario-producto
    """

    driver = None

    try:
        driver = get_neo4j_driver()

        usuarios = dataset["usuarios"]
        productos = dataset["productos"]
        categorias = dataset["categorias"]
        eventos = dataset["eventos"]

        with driver.session() as session:
            if LOAD_MODE == "reset":
                session.run("MATCH (n) DETACH DELETE n")

            for usuario in usuarios:
                session.run("""
                    MERGE (u:Usuario {usuario_id: $usuario_id})
                    SET u.nombre = $nombre,
                        u.email = $email,
                        u.edad = $edad,
                        u.pais = $pais,
                        u.fecha_alta = $fecha_alta
                """, usuario)

            for categoria in categorias:
                session.run("""
                    MERGE (c:Categoria {categoria_id: $categoria_id})
                    SET c.nombre = $nombre,
                        c.descripcion = $descripcion
                """, categoria)

            for producto in productos:
                session.run("""
                    MERGE (p:Producto {producto_id: $producto_id})
                    SET p.nombre = $nombre,
                        p.marca = $marca,
                        p.precio = $precio,
                        p.stock = $stock,
                        p.fecha_alta = $fecha_alta,
                        p.categoria_id = $categoria_id

                    WITH p
                    MATCH (c:Categoria {categoria_id: $categoria_id})
                    MERGE (p)-[:PERTENECE_A]->(c)
                """, producto)

            for evento in eventos:
                relation_type = RELATION_BY_EVENT_TYPE[evento["tipo_evento"]]

                session.run(f"""
                    MATCH (u:Usuario {{usuario_id: $usuario_id}})
                    MATCH (p:Producto {{producto_id: $producto_id}})
                    MERGE (u)-[r:{relation_type}]->(p)
                    ON CREATE SET
                        r.cantidad = 1,
                        r.ultimo_evento = datetime($timestamp)
                    ON MATCH SET
                        r.cantidad = coalesce(r.cantidad, 0) + 1,
                        r.ultimo_evento = datetime($timestamp)
                """, evento)

                session.run("""
                    MATCH (u:Usuario {usuario_id: $usuario_id})
                    MATCH (c:Categoria {categoria_id: $categoria_id})
                    MERGE (u)-[r:INTERESADO_EN]->(c)
                    ON CREATE SET
                        r.cantidad = 1,
                        r.ultimo_evento = datetime($timestamp)
                    ON MATCH SET
                        r.cantidad = coalesce(r.cantidad, 0) + 1,
                        r.ultimo_evento = datetime($timestamp)
                """, evento)

        print(f"Neo4j: {len(usuarios)} usuarios cargados")
        print(f"Neo4j: {len(productos)} productos cargados")
        print(f"Neo4j: {len(categorias)} categorías cargadas")
        print(f"Neo4j: {len(eventos)} eventos procesados como relaciones")

    finally:
        if driver:
            driver.close()