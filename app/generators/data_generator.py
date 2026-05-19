import random
from datetime import datetime, timedelta
from faker import Faker
from app.config import (
    TOTAL_USUARIOS,
    TOTAL_PRODUCTOS,
    TOTAL_CATEGORIAS,
    TOTAL_EVENTOS,
    DATA_SEED,
)

BASE_USER_START_DATE = datetime(2024, 1, 1, 0, 0, 0)
BASE_USER_END_DATE = datetime(2026, 4, 1, 0, 0, 0)

BASE_PRODUCT_START_DATE = datetime(2025, 1, 1, 0, 0, 0)
BASE_PRODUCT_END_DATE = datetime(2026, 5, 1, 0, 0, 0)

BASE_EVENT_START_DATE = datetime(2026, 5, 1, 0, 0, 0)


EVENT_TYPES = ["vista", "click", "busqueda", "compra", "favorito"]

EVENT_WEIGHTS = {
    "vista": 1,
    "click": 2,
    "busqueda": 3,
    "favorito": 4,
    "compra": 5,
}


CATEGORY_NAMES = [
    "Gaming",
    "Tecnología",
    "Audio",
    "Smartphones",
    "Hogar",
    "Electrodomésticos",
    "Moda",
    "Deportes",
    "Fitness",
    "Libros",
    "Juguetes",
    "Automotriz",
    "Belleza",
    "Herramientas",
    "Oficina",
    "Muebles",
    "Mascotas",
    "Instrumentos Musicales",
    "Accesorios",
    "Computación",
]


PRODUCT_BASE_NAMES = [
    "Teclado mecánico",
    "Mouse inalámbrico",
    "Auriculares bluetooth",
    "Monitor LED",
    "Notebook",
    "Silla ergonómica",
    "Cámara web",
    "Micrófono USB",
    "Smartwatch",
    "Parlante portátil",
    "Mochila urbana",
    "Zapatillas deportivas",
    "Cafetera eléctrica",
    "Lámpara LED",
    "Disco SSD",
    "Memoria RAM",
    "Router WiFi",
    "Tablet",
    "Impresora",
    "Joystick inalámbrico",
]


BRANDS = [
    "Logitech",
    "Redragon",
    "Samsung",
    "Lenovo",
    "Sony",
    "Xiaomi",
    "HP",
    "Dell",
    "Acer",
    "Philips",
    "Noblex",
    "Gadnic",
    "Kingston",
    "HyperX",
    "Corsair",
]


COUNTRIES = [
    "Argentina",
    "Uruguay",
    "Chile",
    "Brasil",
    "Paraguay",
]


def generate_categories(fake):
    categories = []

    for index in range(1, TOTAL_CATEGORIAS + 1):
        name = CATEGORY_NAMES[(index - 1) % len(CATEGORY_NAMES)]

        categories.append({
            "categoria_id": f"cat_{index:03d}",
            "nombre": name,
            "descripcion": f"Categoría de productos relacionados con {name.lower()}",
        })

    return categories


def generate_users(fake):
    users = []

    for index in range(1, TOTAL_USUARIOS + 1):
        users.append({
            "usuario_id": f"usr_{index:03d}",
            "nombre": fake.name(),
            "email": f"usuario{index:03d}@example.com",
            "edad": random.randint(18, 65),
            "pais": random.choice(COUNTRIES),
            "fecha_alta": fake.date_time_between(
                start_date=BASE_USER_START_DATE,
                end_date=BASE_USER_END_DATE
            ).isoformat(),
        })

    return users


def generate_products(fake, categories):
    products = []

    for index in range(1, TOTAL_PRODUCTOS + 1):
        category = random.choice(categories)
        base_name = random.choice(PRODUCT_BASE_NAMES)
        brand = random.choice(BRANDS)

        products.append({
            "producto_id": f"prod_{index:03d}",
            "nombre": f"{base_name} {brand} {index}",
            "categoria_id": category["categoria_id"],
            "marca": brand,
            "precio": round(random.uniform(5000, 500000), 2),
            "stock": random.randint(0, 250),
            "fecha_alta": fake.date_time_between(
                start_date="-1y",
                end_date="-1d"
            ).isoformat(),
            "atributos": {
                "color": random.choice(["negro", "blanco", "gris", "azul", "rojo"]),
                "origen": random.choice(["nacional", "importado"]),
                "condicion": random.choice(["nuevo", "reacondicionado"]),
            }
        })

    return products


def generate_events(users, products):
    events = []

    start_date = BASE_EVENT_START_DATE

    for index in range(1, TOTAL_EVENTOS + 1):
        user = random.choice(users)
        product = random.choice(products)

        event_type = random.choices(
            EVENT_TYPES,
            weights=[45, 25, 15, 8, 7],
            k=1
        )[0]

        event_timestamp = start_date + timedelta(
            minutes=random.randint(0, 30 * 24 * 60)
        )

        events.append({
            "evento_id": f"evt_{index:04d}",
            "usuario_id": user["usuario_id"],
            "producto_id": product["producto_id"],
            "categoria_id": product["categoria_id"],
            "tipo_evento": event_type,
            "timestamp": event_timestamp.isoformat(),
            "score_evento": EVENT_WEIGHTS[event_type],
        })

    return events


def generate_dataset():
    """
    Genera el dataset lógico común del proyecto.

    Total esperado por defecto:
    - 50 usuarios
    - 180 productos
    - 20 categorías
    - 750 eventos
    = 1000 registros lógicos

    Todas las bases deben cargar sus datos a partir de este dataset.
    """

    random.seed(DATA_SEED)
    fake = Faker("es_AR")
    Faker.seed(DATA_SEED)

    categories = generate_categories(fake)
    users = generate_users(fake)
    products = generate_products(fake, categories)
    events = generate_events(users, products)

    return {
        "usuarios": users,
        "productos": products,
        "categorias": categories,
        "eventos": events,
        "metadata": {
            "total_usuarios": len(users),
            "total_productos": len(products),
            "total_categorias": len(categories),
            "total_eventos": len(events),
            "total_registros_logicos": (
                    len(users) + len(products) + len(categories) + len(events)
            ),
            "data_seed": DATA_SEED,
        }
    }


def print_dataset_summary(dataset):
    metadata = dataset["metadata"]

    print("Resumen del dataset generado")
    print("-" * 50)
    print(f"Usuarios: {metadata['total_usuarios']}")
    print(f"Productos: {metadata['total_productos']}")
    print(f"Categorías: {metadata['total_categorias']}")
    print(f"Eventos: {metadata['total_eventos']}")
    print(f"Total lógico: {metadata['total_registros_logicos']}")
    print(f"Seed: {metadata['data_seed']}")