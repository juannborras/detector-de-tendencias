import random
from datetime import datetime, timedelta
from faker import Faker
from app.config import (
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


PRODUCT_BASE_NAMES_BY_CATEGORY_ID = {
    "cat_001": [
        "Joystick inalambrico",
        "Teclado mecanico gamer",
        "Mouse gamer",
        "Auriculares gamer",
        "Monitor gaming",
        "Silla gamer",
        "Microfono streaming",
        "Webcam HD",
    ],
    "cat_002": [
        "Smartwatch",
        "Tablet",
        "Router WiFi",
        "Disco SSD",
        "Memoria RAM",
        "Notebook",
        "Hub USB",
        "Power bank",
    ],
    "cat_003": [
        "Auriculares bluetooth",
        "Parlante portatil",
        "Microfono USB",
        "Barra de sonido",
        "Subwoofer",
        "Cable auxiliar",
        "Auriculares inalambricos",
        "Receptor bluetooth",
    ],
    "cat_004": [
        "Smartphone",
        "Cargador rapido",
        "Funda para celular",
        "Vidrio templado",
        "Cable USB-C",
        "Soporte para celular",
        "Power bank",
        "Adaptador de carga",
    ],
    "cat_005": [
        "Lampara LED",
        "Organizador de cocina",
        "Cortina blackout",
        "Almohadon decorativo",
        "Repisa flotante",
        "Difusor de aromas",
        "Perchero de pared",
        "Canasto organizador",
    ],
    "cat_006": [
        "Cafetera electrica",
        "Pava electrica",
        "Tostadora",
        "Licuadora",
        "Aspiradora",
        "Microondas",
        "Procesadora",
        "Plancha a vapor",
    ],
    "cat_007": [
        "Remera basica",
        "Campera urbana",
        "Jean recto",
        "Buzo canguro",
        "Camisa casual",
        "Vestido urbano",
        "Gorra deportiva",
        "Cinturon de cuero",
    ],
    "cat_008": [
        "Zapatillas deportivas",
        "Pelota de futbol",
        "Raqueta de tenis",
        "Mochila deportiva",
        "Botella deportiva",
        "Short deportivo",
        "Remera tecnica",
        "Bolso deportivo",
    ],
    "cat_009": [
        "Mancuernas",
        "Colchoneta yoga",
        "Banda elastica",
        "Soga de salto",
        "Guantes fitness",
        "Rueda abdominal",
        "Tobilleras con peso",
        "Rodillo masajeador",
    ],
    "cat_010": [
        "Novela historica",
        "Libro de programacion",
        "Manual de datos",
        "Libro infantil",
        "Agenda de lectura",
        "Cuaderno de notas",
        "Diccionario bilingue",
        "Libro de negocios",
    ],
    "cat_011": [
        "Bloques de construccion",
        "Muneca articulada",
        "Auto de juguete",
        "Puzzle didactico",
        "Juego de mesa",
        "Peluche",
        "Set de masas",
        "Robot interactivo",
    ],
    "cat_012": [
        "Cargador de bateria",
        "Compresor portatil",
        "Cubre asiento",
        "Alfombra para auto",
        "Soporte para celular",
        "Aspiradora para auto",
        "Kit de luces LED",
        "Organizador de baul",
    ],
    "cat_013": [
        "Crema hidratante",
        "Shampoo reparador",
        "Secador de pelo",
        "Plancha para pelo",
        "Perfume",
        "Set de maquillaje",
        "Cepillo facial",
        "Protector solar",
    ],
    "cat_014": [
        "Taladro percutor",
        "Destornillador electrico",
        "Caja de herramientas",
        "Llave ajustable",
        "Sierra circular",
        "Nivel laser",
        "Martillo",
        "Set de mechas",
    ],
    "cat_015": [
        "Impresora",
        "Silla ergonomica",
        "Escritorio",
        "Resma de papel",
        "Organizador de escritorio",
        "Calculadora",
        "Lampara de escritorio",
        "Mouse inalambrico",
    ],
    "cat_016": [
        "Mesa ratona",
        "Sillon individual",
        "Biblioteca",
        "Mesa de luz",
        "Comoda",
        "Estanteria",
        "Silla de comedor",
        "Rack TV",
    ],
    "cat_017": [
        "Cama para mascota",
        "Comedero",
        "Collar ajustable",
        "Juguete mordillo",
        "Rascador",
        "Correa reforzada",
        "Transportadora",
        "Bebedero automatico",
    ],
    "cat_018": [
        "Guitarra criolla",
        "Teclado musical",
        "Ukelele",
        "Microfono dinamico",
        "Soporte de guitarra",
        "Afinador digital",
        "Bateria electronica",
        "Cable de instrumento",
    ],
    "cat_019": [
        "Mochila urbana",
        "Billetera",
        "Reloj analogico",
        "Lentes de sol",
        "Cartera",
        "Rinonera",
        "Pulsera",
        "Porta notebook",
    ],
    "cat_020": [
        "Notebook",
        "Monitor LED",
        "Teclado mecanico",
        "Mouse inalambrico",
        "Disco SSD",
        "Memoria RAM",
        "Placa de video",
        "Gabinete PC",
    ],
}


PRODUCT_BRANDS_BY_CATEGORY_ID = {
    "cat_001": ["Logitech", "Redragon", "HyperX"],
    "cat_002": ["Samsung", "Xiaomi", "Philips"],
    "cat_003": ["Sony", "JBL", "Philips"],
    "cat_004": ["Samsung", "Motorola", "Xiaomi"],
    "cat_005": ["CasaNoble", "DecoHome", "Lumina"],
    "cat_006": ["Oster", "Atma", "Philips"],
    "cat_007": ["Levis", "Adidas", "Puma"],
    "cat_008": ["Adidas", "Nike", "Topper"],
    "cat_009": ["Everlast", "Randers", "Reebok"],
    "cat_010": ["Planeta", "Sudamericana", "Paidos"],
    "cat_011": ["Lego", "Hasbro", "Mattel"],
    "cat_012": ["Bosch", "Michelin", "Gadnic"],
    "cat_013": ["Nivea", "Revlon", "Loreal"],
    "cat_014": ["Bosch", "Stanley", "Black+Decker"],
    "cat_015": ["HP", "Epson", "Staples"],
    "cat_016": ["Ikea", "Dellacasa", "RapiMueble"],
    "cat_017": ["Purina", "Catit", "Kong"],
    "cat_018": ["Yamaha", "Casio", "Fender"],
    "cat_019": ["Samsonite", "Totto", "Primicia"],
    "cat_020": ["Lenovo", "HP", "Kingston"],
}


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

    for index, category in enumerate(category_assignments, start=1):
        product_names = PRODUCT_BASE_NAMES_BY_CATEGORY_ID.get(
            category["categoria_id"]
        )
        brand_names = PRODUCT_BRANDS_BY_CATEGORY_ID.get(
            category["categoria_id"]
        )

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
    - minimo 5 productos por categoria
    - 1250 eventos
    = 1500 registros lógicos

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
            "min_productos_por_categoria": MIN_PRODUCTOS_POR_CATEGORIA,
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
    print(f"Minimo productos por categoria: {metadata['min_productos_por_categoria']}")
    print(f"Eventos: {metadata['total_eventos']}")
    print(f"Total lógico: {metadata['total_registros_logicos']}")
    print(f"Seed: {metadata['data_seed']}")
