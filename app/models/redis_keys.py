# Convenciones de claves Redis del proyecto

TRENDING_GLOBAL_KEY = "trending:global"
TRENDING_CATEGORY_PREFIX = "trending:cat:"
CACHE_TOP10_GLOBAL_KEY = "cache:top10_global"
EVENT_COUNTER_KEY = "contador:eventos_total"
SESSION_PREFIX = "sesion:"


def setup_redis(redis_client):
    """
    Redis no necesita schema fijo.
    En este setup dejamos registradas claves de metadata para documentar
    la convención usada por el proyecto.
    """

    redis_client.hset(
        "metadata:redis_keys",
        mapping={
            "ranking_global": TRENDING_GLOBAL_KEY,
            "ranking_categoria": f"{TRENDING_CATEGORY_PREFIX}<categoria_id>",
            "cache_top10": CACHE_TOP10_GLOBAL_KEY,
            "contador_eventos": EVENT_COUNTER_KEY,
            "sesion_usuario": f"{SESSION_PREFIX}<usuario_id>",
        }
    )

    redis_client.set("estado:redis_setup", "OK")

    print("Redis setup OK")