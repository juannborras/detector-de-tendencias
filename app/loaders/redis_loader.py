import json
from collections import defaultdict

from app.config import LOAD_MODE
from app.connections import get_redis_client
from app.models.redis_keys import (
    TRENDING_GLOBAL_KEY,
    TRENDING_CATEGORY_PREFIX,
    CACHE_TOP10_GLOBAL_KEY,
    EVENT_COUNTER_KEY,
    SESSION_PREFIX,
)


EVENT_SCORE = {
    "vista": 1,
    "click": 2,
    "busqueda": 3,
    "favorito": 4,
    "compra": 5,
}


def delete_by_pattern(redis_client, pattern):
    keys = list(redis_client.scan_iter(match=pattern))
    if keys:
        redis_client.delete(*keys)


def load_redis(dataset):
    """
    Carga estructuras derivadas en Redis.

    Redis se usa para:
    - ranking global
    - ranking por categoría
    - cache top 10
    - contador de eventos
    - sesiones temporales
    """

    redis_client = get_redis_client()

    eventos = dataset["eventos"]
    usuarios = dataset["usuarios"]

    if LOAD_MODE == "reset":
        delete_by_pattern(redis_client, "trending:*")
        delete_by_pattern(redis_client, "cache:*")
        delete_by_pattern(redis_client, "contador:*")
        delete_by_pattern(redis_client, "sesion:*")

    eventos_por_usuario = defaultdict(int)
    ultima_actividad_usuario = {}

    for evento in eventos:
        producto_id = evento["producto_id"]
        categoria_id = evento["categoria_id"]
        usuario_id = evento["usuario_id"]
        tipo_evento = evento["tipo_evento"]
        timestamp = evento["timestamp"]

        score = EVENT_SCORE.get(tipo_evento, 0)

        redis_client.zincrby(TRENDING_GLOBAL_KEY, score, producto_id)
        redis_client.zincrby(
            f"{TRENDING_CATEGORY_PREFIX}{categoria_id}",
            score,
            producto_id
        )

        redis_client.incr(EVENT_COUNTER_KEY)

        eventos_por_usuario[usuario_id] += 1
        ultima_actividad_usuario[usuario_id] = timestamp

    top10_global = redis_client.zrevrange(
        TRENDING_GLOBAL_KEY,
        0,
        9,
        withscores=True
    )

    redis_client.setex(
        CACHE_TOP10_GLOBAL_KEY,
        300,
        json.dumps(top10_global)
    )

    for usuario in usuarios:
        usuario_id = usuario["usuario_id"]
        session_key = f"{SESSION_PREFIX}{usuario_id}"

        redis_client.hset(
            session_key,
            mapping={
                "usuario_id": usuario_id,
                "email": usuario["email"],
                "eventos_generados": eventos_por_usuario.get(usuario_id, 0),
                "ultima_actividad": ultima_actividad_usuario.get(usuario_id, ""),
            }
        )

        redis_client.expire(session_key, 3600)

    print(f"Redis: {len(eventos)} eventos procesados")
    print(f"Redis: ranking global actualizado")
    print(f"Redis: cache top 10 creado con TTL")
    print(f"Redis: {len(usuarios)} sesiones creadas con TTL")