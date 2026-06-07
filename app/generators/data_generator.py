import json
import random
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

from faker import Faker

from app.config import (
    BASE_DIR,
    DATA_CATALOG_PATH,
    TOTAL_USUARIOS,
    TOTAL_PRODUCTOS,
    TOTAL_CATEGORIAS,
    TOTAL_EVENTOS,
    MIN_PRODUCTOS_POR_CATEGORIA,
    DATA_SEED,
)


BASE_USER_START_DATE = datetime(2024, 1, 1, 0, 0, 0)
BASE_USER_END_DATE = datetime(2026, 4, 1, 0, 0, 0)

BASE_PRODUCT_START_DATE = datetime(2025, 1, 1, 0, 0, 0)
BASE_PRODUCT_END_DATE = datetime(2026, 5, 1, 0, 0, 0)

BASE_EVENT_START_DATE = datetime(2026, 5, 1, 0, 0, 0)

REQUIRED_CATALOG_KEYS = {
    "category_names",
    "product_base_names_by_category_id",
    "product_brands_by_category_id",
    "countries",
    "event_types",
    "event_weights",
    "event_choice_weights",
    "cassandra_summary_field_by_event_type",
    "neo4j_relation_by_event_type",
    "product_attributes",
}


@lru_cache(maxsize=1)
def load_catalog():
    catalog_path = Path(DATA_CATALOG_PATH)
    if not catalog_path.is_absolute():
        catalog_path = BASE_DIR / catalog_path

    with catalog_path.open("r", encoding="utf-8") as catalog_file:
        catalog = json.load(catalog_file)

    missing_keys = REQUIRED_CATALOG_KEYS - set(catalog)
    if missing_keys:
        missing = ", ".join(sorted(missing_keys))
        raise ValueError(f"Faltan claves en el catalogo de datos: {missing}")

    return catalog


def generate_categories(fake, catalog):
    categories = []
    category_names = catalog["category_names"]

    for index in range(1, TOTAL_CATEGORIAS + 1):
        name = category_names[(index - 1) % len(category_names)]

        categories.append({
            "categoria_id": f"cat_{index:03d}",
            "nombre": name,
            "descripcion": f"Categoria de productos relacionados con {name.lower()}",
        })

    return categories


def generate_users(fake, catalog):
    users = []
    countries = catalog["countries"]

    for index in range(1, TOTAL_USUARIOS + 1):
        users.append({
            "usuario_id": f"usr_{index:03d}",
            "nombre": fake.name(),
            "email": f"usuario{index:03d}@example.com",
            "edad": random.randint(18, 65),
            "pais": random.choice(countries),
            "fecha_alta": fake.date_time_between(
                start_date=BASE_USER_START_DATE,
                end_date=BASE_USER_END_DATE
            ).isoformat(),
        })

    return users


def generate_products(fake, categories, catalog):
    products = []

    minimum_required = len(categories) * MIN_PRODUCTOS_POR_CATEGORIA

    if TOTAL_PRODUCTOS < minimum_required:
        raise ValueError(
            "TOTAL_PRODUCTOS no alcanza para garantizar "
            f"{MIN_PRODUCTOS_POR_CATEGORIA} productos por categoria"
        )

    category_assignments = []

    for category in categories:
        category_assignments.extend([category] * MIN_PRODUCTOS_POR_CATEGORIA)

    remaining_products = TOTAL_PRODUCTOS - len(category_assignments)

    for _ in range(remaining_products):
        category_assignments.append(random.choice(categories))

    random.shuffle(category_assignments)

    base_names_by_category = catalog["product_base_names_by_category_id"]
    brands_by_category = catalog["product_brands_by_category_id"]
    attributes = catalog["product_attributes"]

    for index, category in enumerate(category_assignments, start=1):
        product_names = base_names_by_category.get(category["categoria_id"])
        brand_names = brands_by_category.get(category["categoria_id"])

        if not product_names or not brand_names:
            raise ValueError(
                "Faltan nombres base o marcas para la categoria "
                f"{category['categoria_id']}"
            )

        base_name = random.choice(product_names)
        brand = random.choice(brand_names)

        products.append({
            "producto_id": f"prod_{index:03d}",
            "nombre": f"{base_name} {brand} {index}",
            "categoria_id": category["categoria_id"],
            "marca": brand,
            "precio": round(random.uniform(5000, 500000), 2),
            "stock": random.randint(0, 250),
            "fecha_alta": fake.date_time_between(
                start_date=BASE_PRODUCT_START_DATE,
                end_date=BASE_PRODUCT_END_DATE
            ).isoformat(),
            "atributos": {
                "color": random.choice(attributes["color"]),
                "origen": random.choice(attributes["origen"]),
                "condicion": random.choice(attributes["condicion"]),
            }
        })

    return products


def generate_events(users, products, catalog):
    events = []

    event_types = catalog["event_types"]
    event_weights = catalog["event_weights"]
    event_choice_weights = [
        catalog["event_choice_weights"][event_type]
        for event_type in event_types
    ]

    for index in range(1, TOTAL_EVENTOS + 1):
        user = random.choice(users)
        product = random.choice(products)

        event_type = random.choices(
            event_types,
            weights=event_choice_weights,
            k=1
        )[0]

        event_timestamp = BASE_EVENT_START_DATE + timedelta(
            minutes=random.randint(0, 30 * 24 * 60)
        )

        events.append({
            "evento_id": f"evt_{index:04d}",
            "usuario_id": user["usuario_id"],
            "producto_id": product["producto_id"],
            "categoria_id": product["categoria_id"],
            "tipo_evento": event_type,
            "timestamp": event_timestamp.isoformat(),
            "score_evento": event_weights[event_type],
        })

    return events


def generate_dataset():
    """
    Genera el dataset logico comun del proyecto.

    Total esperado por defecto:
    - 50 usuarios
    - 180 productos
    - 20 categorias
    - minimo 5 productos por categoria
    - 1250 eventos
    = 1500 registros logicos

    Todas las bases deben cargar sus datos a partir de este dataset.
    """

    random.seed(DATA_SEED)
    fake = Faker("es_AR")
    Faker.seed(DATA_SEED)

    catalog = load_catalog()
    categories = generate_categories(fake, catalog)
    users = generate_users(fake, catalog)
    products = generate_products(fake, categories, catalog)
    events = generate_events(users, products, catalog)

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
            "min_productos_por_categoria": MIN_PRODUCTOS_POR_CATEGORIA,
            "total_registros_logicos": (
                len(users) + len(products) + len(categories) + len(events)
            ),
            "data_seed": DATA_SEED,
            "catalog_path": str(DATA_CATALOG_PATH),
        }
    }


def print_dataset_summary(dataset):
    metadata = dataset["metadata"]

    print("Resumen del dataset generado")
    print("-" * 50)
    print(f"Usuarios: {metadata['total_usuarios']}")
    print(f"Productos: {metadata['total_productos']}")
    print(f"Categorias: {metadata['total_categorias']}")
    print(f"Minimo productos por categoria: {metadata['min_productos_por_categoria']}")
    print(f"Eventos: {metadata['total_eventos']}")
    print(f"Total logico: {metadata['total_registros_logicos']}")
    print(f"Seed: {metadata['data_seed']}")
    print(f"Catalogo: {metadata['catalog_path']}")
