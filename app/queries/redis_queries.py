import json

from app.connections import get_redis_client
from app.config import QUERY_CATEGORY_TOP_LIMIT, QUERY_SAMPLE_LIMIT, QUERY_TOP_LIMIT
from app.models.redis_keys import (
    TRENDING_GLOBAL_KEY,
    TRENDING_CATEGORY_PREFIX,
    CACHE_TOP10_GLOBAL_KEY,
    EVENT_COUNTER_KEY,
    SESSION_PREFIX,
)


def consulta_ranking_global(limit=QUERY_TOP_LIMIT):
    r = get_redis_client()
    resultados = r.zrevrange(TRENDING_GLOBAL_KEY, 0, limit - 1, withscores=True)
    top10 = [{"producto_id": p, "score": s} for p, s in resultados]

    print(f"\n[1] Ranking global (top {limit}):")
    for i, item in enumerate(top10, 1):
        print(f"  {i:2}. {item['producto_id']} — score: {item['score']:.1f}")

    return top10


def consulta_ranking_por_categoria(limit=QUERY_CATEGORY_TOP_LIMIT):
    r = get_redis_client()
    claves_cat = sorted(r.scan_iter(match=f"{TRENDING_CATEGORY_PREFIX}*"))
    top_por_categoria = {}

    print(f"\n[2] Ranking por categoría (top {limit} por categoría):")
    for clave in claves_cat:
        categoria_id = clave.replace(TRENDING_CATEGORY_PREFIX, "")
        items = r.zrevrange(clave, 0, limit - 1, withscores=True)
        top_por_categoria[categoria_id] = [
            {"producto_id": p, "score": s} for p, s in items
        ]
        print(f"  {categoria_id}:")
        for producto, score in items:
            print(f"    {producto} — score: {score:.1f}")

    return top_por_categoria


def consulta_cache_top10(limit=QUERY_SAMPLE_LIMIT):
    r = get_redis_client()
    cache_raw = r.get(CACHE_TOP10_GLOBAL_KEY)
    ttl = r.ttl(CACHE_TOP10_GLOBAL_KEY)

    print(f"\n[3] Cache top10_global (muestra de {limit}, con TTL):")
    if cache_raw:
        cache = json.loads(cache_raw)
        resultado = [{"producto_id": p, "score": s} for p, s in cache] if cache and isinstance(cache[0], list) else cache
        print(f"  TTL restante: {ttl}s | Productos en cache: {len(resultado)}")
        for item in resultado[:limit]:
            print(f"    {item['producto_id']} — score: {item['score']:.1f}")
        return resultado
    else:
        print("  Cache expirada o no disponible.")
        return []


def consulta_contador_eventos():
    r = get_redis_client()
    contador = r.get(EVENT_COUNTER_KEY)
    total = int(contador) if contador else 0

    print("\n[4] Contador total de eventos:")
    print(f"  Total eventos procesados: {total}")

    return total


def consulta_sesiones(limit=QUERY_SAMPLE_LIMIT):
    r = get_redis_client()
    claves_sesion = list(r.scan_iter(match=f"{SESSION_PREFIX}*"))

    print(f"\n[5] Sesiones de usuarios (muestra de {limit}):")
    print(f"  Sesiones activas en Redis: {len(claves_sesion)}")

    sesiones = []
    for clave in claves_sesion[:limit]:
        datos = r.hgetall(clave)
        ttl_sesion = r.ttl(clave)
        print(
            f"  {datos.get('usuario_id')} | "
            f"email: {datos.get('email')} | "
            f"eventos: {datos.get('eventos_generados')} | "
            f"TTL: {ttl_sesion}s"
        )
        sesiones.append(datos)

    return sesiones


def get_redis_dashboard_data():
    try:
        return {
            "status": "ok",
            "contador_eventos": consulta_contador_eventos(),
            "top_global": consulta_ranking_global(),
            "top_por_categoria": consulta_ranking_por_categoria(),
            "cache_top10_global": consulta_cache_top10(),
            "sesiones_sample": consulta_sesiones(),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "contador_eventos": 0,
            "top_global": [],
            "top_por_categoria": {},
            "cache_top10_global": [],
            "sesiones_sample": [],
        }


def run_redis_queries():
    print("\n" + "=" * 50)
    print("REDIS - Consultas demostrativas")
    print("=" * 50)

    consulta_ranking_global()
    consulta_ranking_por_categoria()
    consulta_cache_top10()
    consulta_contador_eventos()
    consulta_sesiones()

    print("\n" + "=" * 50)
