import json
from datetime import datetime

import plotly.graph_objects as go
from dash import Dash, Input, Output, State, callback_context, dcc, html, no_update

from app.crud_operations import (
    cassandra_delete_daily_summary,
    cassandra_upsert_daily_summary,
    mongo_delete_product,
    mongo_upsert_product,
    neo4j_delete_user_event,
    neo4j_upsert_user_event,
    redis_delete_global_score,
    redis_upsert_global_score,
)
from app.dashboard.dashboard_data import get_dashboard_data
from app.connections import get_mongo_db
from app.queries.mongo_queries import (
    query_categoria_por_id,
    query_producto_por_id,
    query_usuario_por_id,
)
from app.queries.neo4j_queries import TIPOS_INTERACCION


PAGE_STYLE = {
    "minHeight": "100vh",
    "backgroundColor": "#f6f8fb",
    "color": "#172033",
    "fontFamily": "Segoe UI, Arial, sans-serif",
}

CONTENT_STYLE = {
    "maxWidth": "1320px",
    "margin": "0 auto",
    "padding": "24px",
}

SECTION_STYLE = {
    "backgroundColor": "#ffffff",
    "border": "1px solid #d8e0ea",
    "borderRadius": "8px",
    "padding": "18px",
    "marginTop": "16px",
}

GRID_STYLE = {
    "display": "grid",
    "gridTemplateColumns": "repeat(auto-fit, minmax(220px, 1fr))",
    "gap": "12px",
}

TABLE_STYLE = {
    "width": "100%",
    "borderCollapse": "collapse",
    "fontSize": "14px",
}

TH_STYLE = {
    "textAlign": "left",
    "padding": "10px",
    "borderBottom": "1px solid #d8e0ea",
    "backgroundColor": "#f1f4f8",
    "fontWeight": "700",
}

TD_STYLE = {
    "padding": "9px 10px",
    "borderBottom": "1px solid #edf1f5",
    "verticalAlign": "top",
}

INPUT_STYLE = {
    "width": "100%",
    "boxSizing": "border-box",
    "border": "1px solid #b8c4d4",
    "borderRadius": "6px",
    "padding": "9px 10px",
    "fontSize": "14px",
}

SECONDARY_BUTTON_STYLE = {
    "border": "1px solid #1f5fbf",
    "backgroundColor": "#ffffff",
    "color": "#1f5fbf",
    "borderRadius": "6px",
    "padding": "9px 12px",
    "fontWeight": "700",
    "cursor": "pointer",
}

DANGER_BUTTON_STYLE = {
    **SECONDARY_BUTTON_STYLE,
    "border": "1px solid #b42318",
    "color": "#b42318",
}

CRUD_CARD_STYLE = {
    "border": "1px solid #d8e0ea",
    "borderRadius": "8px",
    "padding": "14px",
    "backgroundColor": "#ffffff",
}

TOP_TENDENCIA_COLUMNS = [
    ("Categoria", "categoria_nombre"),
    ("Fecha", "fecha"),
    ("Producto ID", "producto_id"),
    ("Score", "score_tendencia"),
    ("Eventos", "total_eventos"),
    ("Vistas", "total_vistas"),
    ("Clicks", "total_clicks"),
    ("Busquedas", "total_busquedas"),
    ("Favoritos", "total_favoritos"),
    ("Compras", "total_compras"),
]

RESUMEN_DIARIO_COLUMNS = [
    ("Fecha", "fecha"),
    ("Producto ID", "producto_id"),
    ("Categoria", "categoria_nombre"),
    ("Eventos", "total_eventos"),
    ("Vistas", "total_vistas"),
    ("Clicks", "total_clicks"),
    ("Busquedas", "total_busquedas"),
    ("Favoritos", "total_favoritos"),
    ("Compras", "total_compras"),
    ("Score", "score_tendencia"),
]

CASSANDRA_EVENTOS_USUARIO_COLUMNS = [
    ("Usuario ID", "usuario_id"),
    ("Fecha", "fecha"),
    ("Timestamp", "timestamp"),
    ("Evento ID", "evento_id"),
    ("Producto ID", "producto_id"),
    ("Tipo", "tipo_evento"),
    ("Categoria", "categoria_nombre"),
]

NEO4J_USUARIOS_COLUMNS = [
    ("Usuario ID", "usuario_id"),
    ("Nombre", "nombre"),
    ("Eventos", "eventos"),
]

NEO4J_PRODUCTOS_COLUMNS = [
    ("Producto ID", "producto_id"),
    ("Nombre", "nombre"),
    ("Tipo", "tipo_evento"),
    ("Usuarios", "usuarios_distintos"),
    ("Eventos", "total_eventos"),
]

NEO4J_CATEGORIAS_COLUMNS = [
    ("Categoria ID", "categoria_id"),
    ("Categoria", "categoria"),
    ("Usuarios interesados", "usuarios_interesados"),
    ("Eventos interes", "eventos_interes"),
]

NEO4J_USUARIOS_PRODUCTO_COLUMNS = [
    ("Usuario ID", "usuario_id"),
    ("Nombre", "nombre"),
    ("Producto ID", "producto_id"),
    ("Producto", "producto"),
    ("Tipo", "tipo_evento"),
    ("Cantidad", "cantidad"),
    ("Ultimo evento", "ultimo_evento"),
]

NEO4J_RECOMENDACIONES_COLUMNS = [
    ("Usuario ID", "usuario_id"),
    ("Usuario", "usuario"),
    ("Categoria", "categoria"),
    ("Producto recomendado", "producto_recomendado"),
    ("Producto", "producto"),
    ("Motivo", "motivo"),
    ("Afinidad", "afinidad_categoria"),
    ("Popularidad", "popularidad_producto"),
]

REDIS_TOP_GLOBAL_COLUMNS = [
    ("Producto ID", "producto_id"),
    ("Score", "score"),
]

REDIS_TOP_CATEGORIA_COLUMNS = [
    ("Categoria ID", "categoria_id"),
    ("Producto ID", "producto_id"),
    ("Score", "score"),
]

REDIS_SESSION_COLUMNS = [
    ("Usuario ID", "usuario_id"),
    ("Email", "email"),
    ("Eventos", "eventos_generados"),
    ("Ultima actividad", "ultima_actividad"),
    ("TTL", "ttl"),
]

EVENT_OPTIONS = [
    {
        "label": event_type,
        "value": event_type,
    }
    for event_type in TIPOS_INTERACCION
]


def status_color(status):
    if status == "ok":
        return "#16794c"

    if status == "pending":
        return "#9a6700"

    return "#b42318"


def normalize_status(data):
    return data.get("status", "error") if isinstance(data, dict) else "error"


def section_title(title, detail=None):
    children = [
        html.H2(
            title,
            style={
                "fontSize": "20px",
                "margin": "0",
                "letterSpacing": "0",
            },
        )
    ]

    if detail:
        children.append(
            html.P(
                detail,
                style={
                    "margin": "6px 0 0",
                    "color": "#526071",
                    "lineHeight": "1.45",
                },
            )
        )

    return html.Div(children, style={"marginBottom": "14px"})


def status_card(label, data):
    status = normalize_status(data)
    message = data.get("message", "") if isinstance(data, dict) else ""
    error = data.get("error", "") if isinstance(data, dict) else ""

    return html.Div(
        [
            html.Div(label, style={"fontWeight": "700", "fontSize": "15px"}),
            html.Div(
                status.upper(),
                style={
                    "display": "inline-block",
                    "marginTop": "10px",
                    "padding": "4px 8px",
                    "borderRadius": "6px",
                    "backgroundColor": f"{status_color(status)}18",
                    "color": status_color(status),
                    "fontSize": "12px",
                    "fontWeight": "700",
                },
            ),
            html.Div(
                error or message or "Datos disponibles",
                style={
                    "marginTop": "10px",
                    "color": "#526071",
                    "fontSize": "13px",
                    "lineHeight": "1.35",
                },
            ),
        ],
        style={
            "border": "1px solid #d8e0ea",
            "borderRadius": "8px",
            "padding": "14px",
            "backgroundColor": "#ffffff",
        },
    )


def kpi_card(label, value, detail=None):
    return html.Div(
        [
            html.Div(label, style={"fontSize": "13px", "color": "#526071"}),
            html.Div(
                value,
                style={
                    "fontSize": "28px",
                    "fontWeight": "750",
                    "marginTop": "4px",
                },
            ),
            html.Div(
                detail or "",
                style={
                    "fontSize": "12px",
                    "color": "#6b7788",
                    "marginTop": "4px",
                },
            ),
        ],
        style={
            "backgroundColor": "#ffffff",
            "border": "1px solid #d8e0ea",
            "borderRadius": "8px",
            "padding": "14px",
        },
    )


def format_value(value):
    if value is None:
        return ""

    if isinstance(value, float):
        return f"{value:.2f}"

    if isinstance(value, dict):
        return ", ".join(f"{key}: {val}" for key, val in value.items())

    return str(value)


def data_table(rows, columns, empty_message="Sin datos para mostrar"):
    if not rows:
        return html.Div(
            empty_message,
            style={
                "padding": "14px",
                "backgroundColor": "#f8fafc",
                "border": "1px solid #d8e0ea",
                "borderRadius": "8px",
                "color": "#526071",
            },
        )

    return html.Div(
        html.Table(
            [
                html.Thead(
                    html.Tr([
                        html.Th(label, style=TH_STYLE)
                        for label, _ in columns
                    ])
                ),
                html.Tbody([
                    html.Tr([
                        html.Td(format_value(row.get(key)), style=TD_STYLE)
                        for _, key in columns
                    ])
                    for row in rows
                ]),
            ],
            style=TABLE_STYLE,
        ),
        style={
            "overflowX": "auto",
            "border": "1px solid #d8e0ea",
            "borderRadius": "8px",
        },
    )


def document_detail(document, empty_message):
    if not document:
        return html.Div(
            empty_message,
            style={
                "padding": "14px",
                "backgroundColor": "#f8fafc",
                "border": "1px solid #d8e0ea",
                "borderRadius": "8px",
                "color": "#526071",
                "fontSize": "14px",
            },
        )

    return data_table(
        [
            {
                "campo": key,
                "valor": value
            }
            for key, value in document.items()
        ],
        [
            ("Campo", "campo"),
            ("Valor", "valor"),
        ],
    )


def query_execution_detail(query_result):
    if not query_result:
        return None

    details = [
        html.Div(
            "Consulta ejecutada",
            style={"fontWeight": "700", "fontSize": "14px"},
        ),
        html.Pre(
            query_result.get("query", ""),
            style={
                "whiteSpace": "pre-wrap",
                "fontFamily": "Consolas, monospace",
                "fontSize": "12px",
                "backgroundColor": "#f8fafc",
                "border": "1px solid #d8e0ea",
                "borderRadius": "6px",
                "padding": "10px",
                "margin": "8px 0 0",
            },
        ),
    ]

    if "filtro" in query_result:
        details.append(
            html.Div(
                f"Filtro: {format_value(query_result['filtro'])}",
                style={"fontSize": "13px", "color": "#526071", "marginTop": "6px"},
            )
        )

    return html.Div(
        details,
        style={
            "padding": "12px",
            "border": "1px solid #d8e0ea",
            "borderRadius": "8px",
            "backgroundColor": "#ffffff",
            "marginBottom": "10px",
        },
    )


def empty_figure(title, message):
    figure = go.Figure()
    figure.update_layout(
        title=title,
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        height=300,
        margin={"l": 40, "r": 20, "t": 55, "b": 40},
        annotations=[
            {
                "text": message,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {"color": "#526071"},
            }
        ],
    )
    return figure


def bar_figure(rows, x_key, y_key, title, x_title, y_title):
    if not rows:
        return empty_figure(title, "Sin datos disponibles")

    figure = go.Figure(
        data=[
            go.Bar(
                x=[row.get(x_key) for row in rows],
                y=[row.get(y_key) for row in rows],
                marker_color="#2563eb",
            )
        ]
    )
    figure.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        height=330,
        margin={"l": 48, "r": 20, "t": 55, "b": 70},
        font={"family": "Segoe UI, Arial, sans-serif"},
    )
    return figure


def score_formula_card():
    return html.Div(
        [
            html.Div(
                "Formula del score",
                style={"fontWeight": "700", "fontSize": "15px"},
            ),
            html.Div(
                "score = vistas*1 + clicks*2 + busquedas*3 + favoritos*4 + compras*5",
                style={
                    "marginTop": "8px",
                    "fontFamily": "Consolas, monospace",
                    "fontSize": "13px",
                    "color": "#172033",
                    "backgroundColor": "#f8fafc",
                    "border": "1px solid #d8e0ea",
                    "borderRadius": "6px",
                    "padding": "10px",
                },
            ),
        ],
        style={
            "border": "1px solid #d8e0ea",
            "borderRadius": "8px",
            "padding": "14px",
            "backgroundColor": "#ffffff",
            "marginBottom": "14px",
        },
    )


def build_kpis(mongo, cassandra):
    mongo_counts = mongo.get("counts", {}) if isinstance(mongo, dict) else {}
    cassandra_counts = cassandra.get("counts", {}) if isinstance(cassandra, dict) else {}

    return html.Div(
        [
            kpi_card("Usuarios", mongo_counts.get("usuarios", 0), "MongoDB"),
            kpi_card("Productos", mongo_counts.get("productos", 0), "MongoDB"),
            kpi_card("Categorias", mongo_counts.get("categorias", 0), "MongoDB"),
            kpi_card(
                "Eventos logicos",
                cassandra_counts.get("eventos_logicos", 0),
                "Cassandra",
            ),
        ],
        style=GRID_STYLE,
    )


def build_mongo_section(mongo):
    if normalize_status(mongo) != "ok":
        return html.Div(
            [
                section_title(
                    "Catalogo documental",
                    "MongoDB debe estar cargado para mostrar productos, usuarios y categorias.",
                ),
                status_card("MongoDB", mongo),
            ],
            style=SECTION_STYLE,
        )

    productos_por_categoria = mongo.get("productos_por_categoria", [])
    productos_mayor_precio = mongo.get("productos_mayor_precio", [])
    stock_bajo = mongo.get("stock_bajo", [])

    return html.Div(
        [
            section_title(
                "Catalogo documental",
                "MongoDB muestra la base maestra de productos, usuarios y categorias.",
            ),
            dcc.Graph(
                figure=bar_figure(
                    productos_por_categoria,
                    "categoria",
                    "total",
                    "Productos por categoria",
                    "Categoria",
                    "Productos",
                ),
                config={"displayModeBar": False},
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.H3("Productos con stock bajo", style={"fontSize": "16px"}),
                            data_table(
                                stock_bajo,
                                [
                                    ("Producto ID", "producto_id"),
                                    ("Nombre", "nombre"),
                                    ("Stock", "stock"),
                                ],
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.H3("Productos mas caros", style={"fontSize": "16px"}),
                            data_table(
                                productos_mayor_precio,
                                [
                                    ("Producto ID", "producto_id"),
                                    ("Nombre", "nombre"),
                                    ("Precio", "precio"),
                                    ("Categoria", "categoria_nombre"),
                                ],
                            ),
                        ]
                    ),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(auto-fit, minmax(360px, 1fr))",
                    "gap": "16px",
                    "marginTop": "12px",
                },
            ),
            html.Div(
                [
                    html.H3("Busqueda documental por ID", style={"fontSize": "16px"}),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label(
                                        "Categoria ID",
                                        htmlFor="categoria-id-input",
                                        style={"fontWeight": "700", "fontSize": "13px"},
                                    ),
                                    html.Div(
                                        [
                                            dcc.Input(
                                                id="categoria-id-input",
                                                type="text",
                                                placeholder="categoria_id",
                                                style=INPUT_STYLE,
                                            ),
                                            html.Button(
                                                "Buscar categoria",
                                                id="buscar-categoria-button",
                                                n_clicks=0,
                                                style=SECONDARY_BUTTON_STYLE,
                                            ),
                                        ],
                                        style={
                                            "display": "grid",
                                            "gridTemplateColumns": "1fr auto",
                                            "gap": "8px",
                                            "marginTop": "6px",
                                        },
                                    ),
                                    html.Div(id="categoria-id-result", style={"marginTop": "10px"}),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Producto ID",
                                        htmlFor="producto-id-input",
                                        style={"fontWeight": "700", "fontSize": "13px"},
                                    ),
                                    html.Div(
                                        [
                                            dcc.Input(
                                                id="producto-id-input",
                                                type="text",
                                                placeholder="producto_id",
                                                style=INPUT_STYLE,
                                            ),
                                            html.Button(
                                                "Buscar producto",
                                                id="buscar-producto-button",
                                                n_clicks=0,
                                                style=SECONDARY_BUTTON_STYLE,
                                            ),
                                        ],
                                        style={
                                            "display": "grid",
                                            "gridTemplateColumns": "1fr auto",
                                            "gap": "8px",
                                            "marginTop": "6px",
                                        },
                                    ),
                                    html.Div(id="producto-id-result", style={"marginTop": "10px"}),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Label(
                                        "Usuario ID",
                                        htmlFor="usuario-id-input",
                                        style={"fontWeight": "700", "fontSize": "13px"},
                                    ),
                                    html.Div(
                                        [
                                            dcc.Input(
                                                id="usuario-id-input",
                                                type="text",
                                                placeholder="usuario_id",
                                                style=INPUT_STYLE,
                                            ),
                                            html.Button(
                                                "Buscar usuario",
                                                id="buscar-usuario-button",
                                                n_clicks=0,
                                                style=SECONDARY_BUTTON_STYLE,
                                            ),
                                        ],
                                        style={
                                            "display": "grid",
                                            "gridTemplateColumns": "1fr auto",
                                            "gap": "8px",
                                            "marginTop": "6px",
                                        },
                                    ),
                                    html.Div(id="usuario-id-result", style={"marginTop": "10px"}),
                                ]
                            ),
                        ],
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "repeat(auto-fit, minmax(360px, 1fr))",
                            "gap": "16px",
                        },
                    ),
                ],
                style={"marginTop": "16px"},
            ),
        ],
        style=SECTION_STYLE,
    )


def query_mongo_document(query_function, document_id, empty_message):
    client = None

    try:
        normalized_id = (document_id or "").strip()

        if not normalized_id:
            return document_detail(None, "Ingresar un ID para buscar.")

        client, db = get_mongo_db()
        result = query_function(db, normalized_id)
        query_detail = query_execution_detail(result)

        if not result["rows"]:
            return html.Div([
                query_detail,
                document_detail(None, empty_message),
            ])

        return html.Div([
            query_detail,
            document_detail(result["rows"][0], empty_message),
        ])

    except Exception as error:
        return html.Div(
            f"Error al consultar MongoDB: {error}",
            style={
                "padding": "14px",
                "backgroundColor": "#fff4f2",
                "border": "1px solid #f3b8ae",
                "borderRadius": "8px",
                "color": "#b42318",
                "fontSize": "14px",
            },
        )

    finally:
        if client:
            client.close()


def build_fecha_selector(available_dates, selected_fecha):
    if not available_dates:
        return html.Div(
            "No hay fechas disponibles en resumen_diario.",
            style={
                "padding": "14px",
                "backgroundColor": "#f8fafc",
                "border": "1px solid #d8e0ea",
                "borderRadius": "8px",
                "color": "#526071",
                "fontSize": "14px",
            },
        )

    return html.Div(
        [
            html.Label(
                "Fecha de analisis",
                htmlFor="resumen-fecha-dropdown",
                style={"fontWeight": "700", "fontSize": "13px"},
            ),
            dcc.Dropdown(
                id="resumen-fecha-dropdown",
                options=[
                    {
                        "label": fecha,
                        "value": fecha,
                    }
                    for fecha in available_dates
                ],
                value=selected_fecha,
                clearable=False,
                searchable=False,
                style={"fontSize": "14px", "marginTop": "6px"},
            ),
            html.Div(
                id="resumen-fecha-status",
                children=f"{len(available_dates)} fechas disponibles",
                style={
                    "fontSize": "12px",
                    "color": "#6b7788",
                    "marginTop": "6px",
                },
            ),
        ],
        style={
            "maxWidth": "260px",
            "marginBottom": "14px",
        },
    )


def build_cassandra_categoria_selector(category_ids, selected_categoria):
    if not category_ids:
        return html.Div(
            "No hay categorias disponibles para tendencias.",
            style={
                "padding": "14px",
                "backgroundColor": "#f8fafc",
                "border": "1px solid #d8e0ea",
                "borderRadius": "8px",
                "color": "#526071",
                "fontSize": "14px",
            },
        )

    return html.Div(
        [
            html.Label(
                "Categoria para tendencia",
                htmlFor="cassandra-categoria-dropdown",
                style={"fontWeight": "700", "fontSize": "13px"},
            ),
            dcc.Dropdown(
                id="cassandra-categoria-dropdown",
                options=[
                    {
                        "label": categoria_id,
                        "value": categoria_id,
                    }
                    for categoria_id in category_ids
                ],
                value=selected_categoria,
                clearable=False,
                searchable=True,
                style={"fontSize": "14px", "marginTop": "6px"},
            ),
            html.Div(
                "Consulta usando PRIMARY KEY ((categoria_id, fecha), ...)",
                id="cassandra-categoria-status",
                style={
                    "fontSize": "12px",
                    "color": "#6b7788",
                    "marginTop": "6px",
                },
            ),
        ],
        style={
            "maxWidth": "320px",
            "marginBottom": "14px",
        },
    )


def build_cassandra_section(cassandra):
    if normalize_status(cassandra) != "ok":
        return html.Div(
            [
                section_title(
                    "Senales historicas",
                    "Cassandra debe estar cargada para mostrar eventos y tendencias.",
                ),
                status_card("Cassandra", cassandra),
            ],
            style=SECTION_STYLE,
        )

    eventos_por_tipo = cassandra.get("eventos_por_tipo", [])
    tendencias = cassandra.get("top_tendencias_resumen_diario", [])
    tendencias_categoria = cassandra.get("top_tendencias_categoria_fecha", [])
    tendencias_categoria_opciones = cassandra.get("tendencias_categoria_opciones", [])
    resumen = cassandra.get("resumen_diario_sample", [])
    eventos_usuario = cassandra.get("eventos_usuario_sample", [])
    eventos_usuario_context = cassandra.get("eventos_usuario_context", {}) or {}
    available_dates = cassandra.get("resumen_diario_fechas", [])
    selected_fecha = cassandra.get("selected_fecha")
    selected_categoria = cassandra.get("selected_categoria")

    return html.Div(
        [
            section_title(
                "Señales historicas y tendencias",
                "Cassandra concentra los eventos historicos y los resumenes que permiten detectar productos con crecimiento de interes.",
            ),
            score_formula_card(),
            html.Div(
                [
                    build_fecha_selector(available_dates, selected_fecha),
                    build_cassandra_categoria_selector(
                        tendencias_categoria_opciones,
                        selected_categoria,
                    ),
                ],
                style={
                    "display": "flex",
                    "gap": "16px",
                    "alignItems": "flex-start",
                    "flexWrap": "wrap",
                },
            ),
            html.Div(
                [
                    dcc.Graph(
                        id="eventos-por-tipo-graph",
                        figure=bar_figure(
                            eventos_por_tipo,
                            "tipo_evento",
                            "total",
                            "Eventos por tipo",
                            "Tipo de evento",
                            "Total",
                        ),
                        config={"displayModeBar": False},
                    ),
                    dcc.Graph(
                        id="top-diario-graph",
                        figure=bar_figure(
                            tendencias,
                            "producto_id",
                            "score_tendencia",
                            "Top diario de productos tendencia",
                            "Producto",
                            "Score",
                        ),
                        config={"displayModeBar": False},
                    ),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(auto-fit, minmax(360px, 1fr))",
                    "gap": "16px",
                },
            ),
            html.Div(
                [
                    html.H3("Top por categoria y fecha", style={"fontSize": "16px"}),
                    html.Div(
                        id="top-categoria-table",
                        children=data_table(
                            tendencias_categoria,
                            TOP_TENDENCIA_COLUMNS,
                        ),
                    ),
                ],
                style={"marginTop": "12px"},
            ),
            html.Div(
                [
                    html.H3("Eventos por usuario y fecha", style={"fontSize": "16px"}),
                    html.Div(
                        [
                            dcc.Input(
                                id="cassandra-usuario-id-input",
                                type="text",
                                value=eventos_usuario_context.get("usuario_id") or "",
                                placeholder="usuario_id",
                                style=INPUT_STYLE,
                            ),
                            html.Button(
                                "Buscar eventos",
                                id="cassandra-usuario-eventos-button",
                                n_clicks=0,
                                style=SECONDARY_BUTTON_STYLE,
                            ),
                        ],
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "minmax(180px, 260px) auto",
                            "gap": "8px",
                            "alignItems": "center",
                            "maxWidth": "480px",
                        },
                    ),
                    html.Div(
                        id="cassandra-usuario-eventos-status",
                        children=(
                            f"Partition key: usuario_id="
                            f"{eventos_usuario_context.get('usuario_id') or 'sin muestra'} "
                            f"+ fecha={eventos_usuario_context.get('fecha') or selected_fecha}"
                        ),
                        style={
                            "fontSize": "12px",
                            "color": "#6b7788",
                            "marginTop": "8px",
                        },
                    ),
                    html.Div(
                        id="cassandra-usuario-eventos-table",
                        children=data_table(
                            eventos_usuario,
                            CASSANDRA_EVENTOS_USUARIO_COLUMNS,
                        ),
                        style={"marginTop": "10px"},
                    ),
                ],
                style={"marginTop": "12px"},
            ),
            html.Div(
                [
                    html.H3("Consulta resumen_diario por fecha", style={"fontSize": "16px"}),
                    html.Div(
                        id="resumen-diario-table",
                        children=data_table(resumen, RESUMEN_DIARIO_COLUMNS),
                    ),
                ],
                style={"marginTop": "12px"},
            ),
        ],
        style=SECTION_STYLE,
    )


def cypher_detail(query):
    return html.Details(
        [
            html.Summary(
                query.get("descripcion", query.get("query", "Consulta")),
                style={"cursor": "pointer", "fontWeight": "700"},
            ),
            html.Pre(
                query.get("cypher", ""),
                style={
                    "whiteSpace": "pre-wrap",
                    "fontFamily": "Consolas, monospace",
                    "fontSize": "12px",
                    "backgroundColor": "#f8fafc",
                    "border": "1px solid #d8e0ea",
                    "borderRadius": "6px",
                    "padding": "10px",
                    "margin": "10px 0 0",
                },
            ),
            html.Div(
                f"Parametros: {format_value(query.get('params', {}))}",
                style={"fontSize": "13px", "color": "#526071", "marginTop": "6px"},
            ),
        ],
        style={
            "border": "1px solid #d8e0ea",
            "borderRadius": "8px",
            "padding": "12px",
            "backgroundColor": "#ffffff",
        },
    )


def build_neo4j_section(neo4j_data):
    if normalize_status(neo4j_data) != "ok":
        return html.Div(
            [
                section_title(
                    "Grafo de relaciones",
                    "Neo4j debe estar cargado para mostrar usuarios, productos e interacciones.",
                ),
                status_card("Neo4j", neo4j_data),
            ],
            style=SECTION_STYLE,
        )

    counts = neo4j_data.get("counts", {})
    usuarios = neo4j_data.get("usuarios_mas_activos", [])
    productos = neo4j_data.get("productos_por_evento", [])
    categorias = neo4j_data.get("categorias_con_mas_interes", [])
    usuarios_producto = neo4j_data.get("usuarios_por_producto_evento", [])
    usuarios_producto_context = neo4j_data.get("usuarios_producto_evento_context", {})
    recomendaciones = neo4j_data.get("recomendaciones_sample", [])
    queries = neo4j_data.get("queries", [])
    selected_tipo_evento = neo4j_data.get("selected_tipo_evento") or "COMPRO"
    selected_producto_id = usuarios_producto_context.get("producto_id") or ""
    selected_producto_evento = usuarios_producto_context.get("tipo_evento") or "COMPRO"

    return html.Div(
        [
            section_title(
                "Grafo de relaciones",
                "Neo4j muestra conexiones entre usuarios, productos, categorias e interacciones.",
            ),
            html.Div(
                [
                    kpi_card("Usuarios", counts.get("usuarios", 0), "Neo4j"),
                    kpi_card("Productos", counts.get("productos", 0), "Neo4j"),
                    kpi_card("Categorias", counts.get("categorias", 0), "Neo4j"),
                    kpi_card(
                        "Eventos representados",
                        counts.get("eventos_representados", 0),
                        "Relaciones agregadas",
                    ),
                ],
                style=GRID_STYLE,
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label(
                                "Tipo de evento",
                                htmlFor="neo4j-event-type-dropdown",
                                style={"fontWeight": "700", "fontSize": "13px"},
                            ),
                            dcc.Dropdown(
                                id="neo4j-event-type-dropdown",
                                options=EVENT_OPTIONS,
                                value=selected_tipo_evento,
                                clearable=False,
                                searchable=False,
                                style={"fontSize": "14px", "marginTop": "6px"},
                            ),
                        ],
                        style={"maxWidth": "260px"},
                    ),
                    dcc.Graph(
                        id="neo4j-productos-evento-graph",
                        figure=bar_figure(
                            productos,
                            "producto_id",
                            "total_eventos",
                            "Productos por tipo de evento",
                            "Producto",
                            "Eventos",
                        ),
                        config={"displayModeBar": False},
                    ),
                    html.Div(
                        [
                            html.H3(
                                "Productos con mas eventos del tipo elegido",
                                style={"fontSize": "16px"},
                            ),
                            html.Div(
                                id="neo4j-productos-evento-table",
                                children=data_table(productos, NEO4J_PRODUCTOS_COLUMNS),
                            ),
                        ]
                    ),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(auto-fit, minmax(280px, 1fr))",
                    "gap": "16px",
                    "marginTop": "14px",
                    "alignItems": "start",
                },
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.H3("Usuarios mas activos", style={"fontSize": "16px"}),
                            data_table(usuarios, NEO4J_USUARIOS_COLUMNS),
                        ]
                    ),
                    html.Div(
                        [
                            html.H3("Categorias con mas interes", style={"fontSize": "16px"}),
                            data_table(categorias, NEO4J_CATEGORIAS_COLUMNS),
                        ]
                    ),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(auto-fit, minmax(360px, 1fr))",
                    "gap": "16px",
                    "marginTop": "14px",
                },
            ),
            html.Div(
                [
                    html.H3("Usuarios por producto y evento", style={"fontSize": "16px"}),
                    html.Div(
                        [
                            dcc.Input(
                                id="neo4j-producto-evento-input",
                                type="text",
                                value=selected_producto_id,
                                placeholder="producto_id",
                                style=INPUT_STYLE,
                            ),
                            dcc.Dropdown(
                                id="neo4j-producto-evento-dropdown",
                                options=EVENT_OPTIONS,
                                value=selected_producto_evento,
                                clearable=False,
                                searchable=False,
                                style={"fontSize": "14px"},
                            ),
                            html.Button(
                                "Buscar usuarios",
                                id="neo4j-producto-evento-button",
                                n_clicks=0,
                                style=SECONDARY_BUTTON_STYLE,
                            ),
                        ],
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "minmax(180px, 1fr) 180px auto",
                            "gap": "8px",
                            "alignItems": "center",
                        },
                    ),
                    html.Div(
                        id="neo4j-usuarios-producto-status",
                        children=(
                            f"Producto: {selected_producto_id or 'sin muestra'} - "
                            f"Evento: {selected_producto_evento}"
                        ),
                        style={
                            "fontSize": "12px",
                            "color": "#6b7788",
                            "marginTop": "8px",
                        },
                    ),
                    html.Div(
                        id="neo4j-usuarios-producto-table",
                        children=data_table(
                            usuarios_producto,
                            NEO4J_USUARIOS_PRODUCTO_COLUMNS,
                        ),
                        style={"marginTop": "10px"},
                    ),
                ],
                style={"marginTop": "14px"},
            ),
            html.Div(
                [
                    html.H3("Recomendaciones por grafo", style={"fontSize": "16px"}),
                    data_table(recomendaciones, NEO4J_RECOMENDACIONES_COLUMNS),
                ],
                style={"marginTop": "14px"},
            ),
            html.Div(
                [
                    html.H3("Cypher ejecutado", style={"fontSize": "16px"}),
                    html.Div(
                        [cypher_detail(query) for query in queries],
                        id="neo4j-query-details",
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "repeat(auto-fit, minmax(360px, 1fr))",
                            "gap": "12px",
                        },
                    ),
                ],
                style={"marginTop": "14px"},
            ),
        ],
        style=SECTION_STYLE,
    )


def flatten_redis_category_rankings(top_por_categoria):
    rows = []

    for categoria_id, items in (top_por_categoria or {}).items():
        for item in items:
            rows.append({
                "categoria_id": categoria_id,
                "producto_id": item.get("producto_id"),
                "score": item.get("score"),
            })

    return rows


def build_redis_section(redis_data):
    if normalize_status(redis_data) != "ok":
        return html.Div(
            [
                section_title(
                    "Estado Redis",
                    "Redis debe estar cargado para mostrar rankings, cache y sesiones.",
                ),
                status_card("Redis", redis_data),
            ],
            style=SECTION_STYLE,
        )

    top_global = redis_data.get("top_global", [])
    top_por_categoria = flatten_redis_category_rankings(
        redis_data.get("top_por_categoria", {})
    )
    cache_top10 = redis_data.get("cache_top10_global", [])
    sesiones = redis_data.get("sesiones_sample", [])
    contador_eventos = redis_data.get("contador_eventos", 0)

    return html.Div(
        [
            section_title(
                "Redis operativo",
                "Redis mantiene rankings, cache, contador de eventos y sesiones temporales.",
            ),
            html.Div(
                [
                    kpi_card("Eventos procesados", contador_eventos, "contador:eventos_total"),
                    kpi_card("Productos en ranking", len(top_global), "trending:global"),
                    kpi_card("Categorias rankeadas", len(redis_data.get("top_por_categoria", {})), "trending:cat:*"),
                    kpi_card("Sesiones muestra", len(sesiones), "sesion:*"),
                ],
                style=GRID_STYLE,
            ),
            html.Div(
                [
                    dcc.Graph(
                        figure=bar_figure(
                            top_global,
                            "producto_id",
                            "score",
                            "Ranking global Redis",
                            "Producto",
                            "Score",
                        ),
                        config={"displayModeBar": False},
                    ),
                    html.Div(
                        [
                            html.H3("Top global", style={"fontSize": "16px"}),
                            data_table(top_global, REDIS_TOP_GLOBAL_COLUMNS),
                        ]
                    ),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(auto-fit, minmax(360px, 1fr))",
                    "gap": "16px",
                    "marginTop": "14px",
                },
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.H3("Ranking por categoria", style={"fontSize": "16px"}),
                            data_table(top_por_categoria, REDIS_TOP_CATEGORIA_COLUMNS),
                        ]
                    ),
                    html.Div(
                        [
                            html.H3("Cache top global", style={"fontSize": "16px"}),
                            data_table(cache_top10, REDIS_TOP_GLOBAL_COLUMNS),
                        ]
                    ),
                ],
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(auto-fit, minmax(360px, 1fr))",
                    "gap": "16px",
                    "marginTop": "14px",
                },
            ),
            html.Div(
                [
                    html.H3("Sesiones de usuario", style={"fontSize": "16px"}),
                    data_table(sesiones, REDIS_SESSION_COLUMNS),
                ],
                style={"marginTop": "14px"},
            ),
        ],
        style=SECTION_STYLE,
    )


def crud_input(component_id, label, input_type="text", placeholder=None):
    return html.Div(
        [
            html.Label(
                label,
                htmlFor=component_id,
                style={"fontWeight": "700", "fontSize": "13px"},
            ),
            dcc.Input(
                id=component_id,
                type=input_type,
                placeholder=placeholder or label,
                style={**INPUT_STYLE, "marginTop": "6px"},
            ),
        ]
    )


def crud_form(title, fields, button_text, button_id, result_id, danger=False):
    return html.Div(
        [
            html.H3(title, style={"fontSize": "16px", "marginTop": "0"}),
            html.Div(
                fields,
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(auto-fit, minmax(180px, 1fr))",
                    "gap": "10px",
                },
            ),
            html.Button(
                button_text,
                id=button_id,
                n_clicks=0,
                style={
                    **(DANGER_BUTTON_STYLE if danger else SECONDARY_BUTTON_STYLE),
                    "marginTop": "12px",
                },
            ),
            html.Div(id=result_id, style={"marginTop": "12px"}),
        ],
        style=CRUD_CARD_STYLE,
    )


def operation_result_view(result):
    if not result:
        return ""

    status = result.get("status", "error")
    verification = result.get("verification", {})
    title = (
        f"{result.get('engine', 'Motor')} - "
        f"{result.get('operation', 'operacion')}"
    )

    return html.Div(
        [
            html.Div(title, style={"fontWeight": "700"}),
            html.Div(
                "VERIFICADO" if verification.get("verified") else "ERROR",
                style={
                    "display": "inline-block",
                    "marginTop": "8px",
                    "padding": "4px 8px",
                    "borderRadius": "6px",
                    "backgroundColor": f"{status_color(status)}18",
                    "color": status_color(status),
                    "fontSize": "12px",
                    "fontWeight": "700",
                },
            ),
            html.Pre(
                json.dumps(result, indent=2, ensure_ascii=False, default=str),
                style={
                    "whiteSpace": "pre-wrap",
                    "fontFamily": "Consolas, monospace",
                    "fontSize": "12px",
                    "backgroundColor": "#f8fafc",
                    "border": "1px solid #d8e0ea",
                    "borderRadius": "6px",
                    "padding": "10px",
                    "margin": "10px 0 0",
                },
            ),
        ],
        style={
            "border": "1px solid #d8e0ea",
            "borderRadius": "8px",
            "padding": "12px",
            "backgroundColor": "#ffffff",
        },
    )


def operation_error_view(error):
    return html.Div(
        str(error),
        style={
            "padding": "12px",
            "backgroundColor": "#fff4f2",
            "border": "1px solid #f3b8ae",
            "borderRadius": "8px",
            "color": "#b42318",
            "fontSize": "14px",
        },
    )


def run_crud_operation(operation, *args):
    view, _ = execute_crud_operation(operation, *args)
    return view


def execute_crud_operation(operation, *args):
    try:
        result = operation(*args)
        return operation_result_view(result), result
    except Exception as error:
        return operation_error_view(error), None


def crud_result_is_verified(result):
    return (
        isinstance(result, dict)
        and result.get("status") == "ok"
        and result.get("verification", {}).get("verified")
    )


def next_cassandra_refresh_token(current_token, fecha):
    version = 0

    if isinstance(current_token, dict):
        version = int(current_token.get("version") or 0)

    return {
        "version": version + 1,
        "fecha": fecha or None,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def next_redis_refresh_token(current_token):
    version = 0

    if isinstance(current_token, dict):
        version = int(current_token.get("version") or 0)

    return {
        "version": version + 1,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def product_upsert_fields(prefix):
    return [
        crud_input(f"{prefix}-producto-id", "producto_id"),
        crud_input(f"{prefix}-nombre", "nombre"),
        crud_input(f"{prefix}-categoria-id", "categoria_id"),
        crud_input(f"{prefix}-marca", "marca"),
        crud_input(f"{prefix}-precio", "precio", "number"),
        crud_input(f"{prefix}-stock", "stock", "number"),
    ]


def neo4j_event_upsert_fields(prefix):
    return [
        crud_input(f"{prefix}-usuario-id", "usuario_id"),
        crud_input(f"{prefix}-producto-id", "producto_id"),
        crud_input(
            f"{prefix}-tipo-evento",
            "tipo_evento",
            placeholder="VIO/CLICK/BUSCO/FAVORITO/COMPRO",
        ),
    ]


def neo4j_event_delete_fields(prefix):
    return [
        crud_input(f"{prefix}-usuario-id", "usuario_id"),
        crud_input(f"{prefix}-producto-id", "producto_id"),
        crud_input(
            f"{prefix}-tipo-evento",
            "tipo_evento",
            placeholder="VIO/CLICK/BUSCO/FAVORITO/COMPRO",
        ),
    ]


def build_crud_screen():
    return html.Div(
        [
            section_title(
                "Operaciones CRUD",
                "Cada operacion usa datos ingresados en vivo y lee nuevamente la base para verificar el resultado.",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            section_title("MongoDB"),
                            html.Div(
                                [
                                    crud_form(
                                        "Crear o actualizar producto",
                                        product_upsert_fields("mongo-upsert"),
                                        "Guardar producto",
                                        "mongo-upsert-button",
                                        "mongo-upsert-result",
                                    ),
                                    crud_form(
                                        "Eliminar producto",
                                        [
                                            crud_input(
                                                "mongo-delete-producto-id",
                                                "producto_id",
                                            )
                                        ],
                                        "Eliminar producto",
                                        "mongo-delete-button",
                                        "mongo-delete-result",
                                        danger=True,
                                    ),
                                ],
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "repeat(auto-fit, minmax(360px, 1fr))",
                                    "gap": "12px",
                                },
                            ),
                        ],
                        style=SECTION_STYLE,
                    ),
                    html.Div(
                        [
                            section_title("Cassandra"),
                            html.Div(
                                [
                                    crud_form(
                                        "Crear o actualizar resumen diario",
                                        [
                                            crud_input(
                                                "cassandra-fecha",
                                                "fecha",
                                                placeholder="YYYY-MM-DD",
                                            ),
                                            crud_input("cassandra-producto-id", "producto_id"),
                                            crud_input("cassandra-categoria-id", "categoria_id"),
                                            crud_input("cassandra-total-eventos", "total_eventos", "number"),
                                            crud_input("cassandra-total-vistas", "total_vistas", "number"),
                                            crud_input("cassandra-total-clicks", "total_clicks", "number"),
                                            crud_input("cassandra-total-busquedas", "total_busquedas", "number"),
                                            crud_input("cassandra-total-favoritos", "total_favoritos", "number"),
                                            crud_input("cassandra-total-compras", "total_compras", "number"),
                                            crud_input("cassandra-score", "score_tendencia", "number"),
                                        ],
                                        "Guardar resumen",
                                        "cassandra-upsert-button",
                                        "cassandra-upsert-result",
                                    ),
                                    crud_form(
                                        "Eliminar resumen diario",
                                        [
                                            crud_input(
                                                "cassandra-delete-fecha",
                                                "fecha",
                                                placeholder="YYYY-MM-DD",
                                            ),
                                            crud_input("cassandra-delete-producto-id", "producto_id"),
                                        ],
                                        "Eliminar resumen",
                                        "cassandra-delete-button",
                                        "cassandra-delete-result",
                                        danger=True,
                                    ),
                                ],
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "repeat(auto-fit, minmax(360px, 1fr))",
                                    "gap": "12px",
                                },
                            ),
                        ],
                        style=SECTION_STYLE,
                    ),
                    html.Div(
                        [
                            section_title("Redis"),
                            html.Div(
                                [
                                    crud_form(
                                        "Crear o actualizar score global",
                                        [
                                            crud_input("redis-producto-id", "producto_id"),
                                            crud_input(
                                                "redis-categoria-id",
                                                "categoria_id",
                                                placeholder="Opcional si el producto existe en MongoDB",
                                            ),
                                            crud_input("redis-score", "score", "number"),
                                        ],
                                        "Guardar score",
                                        "redis-upsert-button",
                                        "redis-upsert-result",
                                    ),
                                    crud_form(
                                        "Eliminar score global",
                                        [
                                            crud_input("redis-delete-producto-id", "producto_id"),
                                        ],
                                        "Eliminar score",
                                        "redis-delete-button",
                                        "redis-delete-result",
                                        danger=True,
                                    ),
                                ],
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "repeat(auto-fit, minmax(360px, 1fr))",
                                    "gap": "12px",
                                },
                            ),
                        ],
                        style=SECTION_STYLE,
                    ),
                    html.Div(
                        [
                            section_title("Neo4j"),
                            html.Div(
                                [
                                    crud_form(
                                        "Registrar evento usuario-producto",
                                        neo4j_event_upsert_fields("neo4j-upsert"),
                                        "Guardar evento",
                                        "neo4j-upsert-button",
                                        "neo4j-upsert-result",
                                    ),
                                    crud_form(
                                        "Eliminar relacion usuario-producto",
                                        neo4j_event_delete_fields("neo4j-delete"),
                                        "Eliminar relacion",
                                        "neo4j-delete-button",
                                        "neo4j-delete-result",
                                        danger=True,
                                    ),
                                ],
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "repeat(auto-fit, minmax(360px, 1fr))",
                                    "gap": "12px",
                                },
                            ),
                        ],
                        style=SECTION_STYLE,
                    ),
                ]
            ),
        ]
    )


def build_dashboard(data):
    mongo = data.get("mongo", {})
    cassandra = data.get("cassandra", {})
    redis_data = data.get("redis", {})
    neo4j_data = data.get("neo4j", {})

    return html.Div(
        [
            html.Div(
                [
                    status_card("MongoDB", mongo),
                    status_card("Cassandra", cassandra),
                    status_card("Redis", redis_data),
                    status_card("Neo4j", neo4j_data),
                ],
                style=GRID_STYLE,
            ),
            html.Div(
                [
                    section_title(
                        "Lectura general",
                        "El detector combina catalogo y eventos. MongoDB aporta el contexto de productos y categorias; Cassandra aporta las senales historicas que producen el score de tendencia.",
                    ),
                    build_kpis(mongo, cassandra),
                ],
                style=SECTION_STYLE,
            ),
            build_cassandra_section(cassandra),
            build_mongo_section(mongo),
            build_neo4j_section(neo4j_data),
            build_redis_section(redis_data),
        ]
    )


def create_dashboard_app():
    dashboard_app = Dash(
        __name__,
        title="Detector de Tendencias",
        suppress_callback_exceptions=True,
    )

    dashboard_app.layout = html.Div(
        html.Div(
            [
                dcc.Store(
                    id="cassandra-crud-refresh-token",
                    data={"version": 0, "fecha": None},
                ),
                dcc.Store(
                    id="redis-crud-refresh-token",
                    data={"version": 0},
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.H1(
                                    "Detector de tendencias ocultas",
                                    style={
                                        "fontSize": "28px",
                                        "margin": "0",
                                        "letterSpacing": "0",
                                    },
                                ),
                                html.P(
                                    "Vista operativa del TPI: datos maestros, eventos historicos y senales de tendencia.",
                                    style={
                                        "margin": "8px 0 0",
                                        "color": "#526071",
                                        "lineHeight": "1.45",
                                    },
                                ),
                            ]
                        ),
                        html.Div(
                            [
                                html.Button(
                                    "Actualizar datos",
                                    id="refresh-button",
                                    n_clicks=0,
                                    style={
                                        "border": "1px solid #1f5fbf",
                                        "backgroundColor": "#2563eb",
                                        "color": "#ffffff",
                                        "borderRadius": "6px",
                                        "padding": "10px 14px",
                                        "fontWeight": "700",
                                        "cursor": "pointer",
                                    },
                                ),
                                html.Div(
                                    id="last-refresh",
                                    style={
                                        "fontSize": "12px",
                                        "color": "#6b7788",
                                        "marginTop": "8px",
                                        "textAlign": "right",
                                    },
                                ),
                            ],
                            style={"minWidth": "180px"},
                        ),
                    ],
                    style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "gap": "16px",
                        "alignItems": "flex-start",
                        "borderBottom": "1px solid #d8e0ea",
                        "paddingBottom": "18px",
                        "marginBottom": "16px",
                    },
                ),
                dcc.Tabs(
                    id="main-tabs",
                    value="lectura",
                    children=[
                        dcc.Tab(
                            label="Dashboard",
                            value="lectura",
                            children=[
                                html.Div(id="dashboard-body"),
                            ],
                        ),
                        dcc.Tab(
                            label="Operaciones CRUD",
                            value="crud",
                            children=[
                                build_crud_screen(),
                            ],
                        ),
                    ],
                ),
            ],
            style=CONTENT_STYLE,
        ),
        style=PAGE_STYLE,
    )

    @dashboard_app.callback(
        Output("dashboard-body", "children"),
        Output("last-refresh", "children"),
        Input("refresh-button", "n_clicks"),
        Input("cassandra-crud-refresh-token", "data"),
        Input("redis-crud-refresh-token", "data"),
    )
    def refresh_dashboard(_, cassandra_crud_refresh, _redis_crud_refresh):
        loaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cassandra_fecha = None
        triggered = (
            callback_context.triggered[0]["prop_id"].split(".")[0]
            if callback_context.triggered
            else None
        )

        if (
            triggered == "cassandra-crud-refresh-token"
            and isinstance(cassandra_crud_refresh, dict)
        ):
            cassandra_fecha = cassandra_crud_refresh.get("fecha")

        return (
            build_dashboard(get_dashboard_data(cassandra_fecha=cassandra_fecha)),
            f"Ultima lectura: {loaded_at}",
        )

    @dashboard_app.callback(
        Output("eventos-por-tipo-graph", "figure"),
        Output("top-diario-graph", "figure"),
        Output("resumen-diario-table", "children"),
        Output("top-categoria-table", "children"),
        Output("resumen-fecha-status", "children"),
        Output("cassandra-categoria-status", "children"),
        Input("resumen-fecha-dropdown", "value"),
        Input("cassandra-categoria-dropdown", "value"),
    )
    def actualizar_resumen_diario(fecha, categoria_id):
        data = get_dashboard_data(
            cassandra_fecha=fecha,
            cassandra_categoria_id=categoria_id,
        )
        cassandra = data.get("cassandra", {})

        if normalize_status(cassandra) != "ok":
            message = cassandra.get("error") or cassandra.get("message") or "Error en Cassandra"
            return (
                empty_figure("Eventos por tipo", message),
                empty_figure("Top diario de productos tendencia", message),
                data_table([], RESUMEN_DIARIO_COLUMNS),
                data_table([], TOP_TENDENCIA_COLUMNS),
                message,
                message,
            )

        eventos_por_tipo = cassandra.get("eventos_por_tipo", [])
        tendencias = cassandra.get("top_tendencias_resumen_diario", [])
        tendencias_categoria = cassandra.get("top_tendencias_categoria_fecha", [])
        resumen = cassandra.get("resumen_diario_sample", [])
        available_dates = cassandra.get("resumen_diario_fechas", [])
        selected_fecha = cassandra.get("selected_fecha") or fecha
        selected_categoria = cassandra.get("selected_categoria") or categoria_id

        status = (
            f"Fecha seleccionada: {selected_fecha} - "
            f"{len(available_dates)} fechas disponibles"
        )
        categoria_status = (
            "Consulta tendencias_por_categoria_fecha con partition key: "
            f"categoria_id={selected_categoria} + fecha={selected_fecha}"
        )

        return (
            bar_figure(
                eventos_por_tipo,
                "tipo_evento",
                "total",
                "Eventos por tipo",
                "Tipo de evento",
                "Total",
            ),
            bar_figure(
                tendencias,
                "producto_id",
                "score_tendencia",
                "Top diario de productos tendencia",
                "Producto",
                "Score",
            ),
            data_table(resumen, RESUMEN_DIARIO_COLUMNS),
            data_table(tendencias_categoria, TOP_TENDENCIA_COLUMNS),
            status,
            categoria_status,
        )

    @dashboard_app.callback(
        Output("cassandra-usuario-eventos-status", "children"),
        Output("cassandra-usuario-eventos-table", "children"),
        Input("cassandra-usuario-eventos-button", "n_clicks"),
        State("cassandra-usuario-id-input", "value"),
        State("resumen-fecha-dropdown", "value"),
        prevent_initial_call=True,
    )
    def buscar_eventos_cassandra_por_usuario(_, usuario_id, fecha):
        data = get_dashboard_data(
            cassandra_fecha=fecha,
            cassandra_usuario_id=usuario_id,
        )
        cassandra = data.get("cassandra", {})

        if normalize_status(cassandra) != "ok":
            message = cassandra.get("error") or cassandra.get("message") or "Error en Cassandra"
            return message, data_table([], CASSANDRA_EVENTOS_USUARIO_COLUMNS, message)

        rows = cassandra.get("eventos_usuario_sample", [])
        context = cassandra.get("eventos_usuario_context", {}) or {}
        status = (
            "Consulta eventos_por_usuario con partition key: "
            f"usuario_id={context.get('usuario_id') or usuario_id} + "
            f"fecha={context.get('fecha') or fecha}"
        )

        return status, data_table(rows, CASSANDRA_EVENTOS_USUARIO_COLUMNS)

    @dashboard_app.callback(
        Output("neo4j-productos-evento-graph", "figure"),
        Output("neo4j-productos-evento-table", "children"),
        Input("neo4j-event-type-dropdown", "value"),
    )
    def actualizar_productos_neo4j_por_evento(tipo_evento):
        data = get_dashboard_data(neo4j_tipo_evento=tipo_evento)
        neo4j_data = data.get("neo4j", {})

        if normalize_status(neo4j_data) != "ok":
            message = neo4j_data.get("error") or neo4j_data.get("message") or "Error en Neo4j"
            return (
                empty_figure("Productos por tipo de evento", message),
                data_table([], NEO4J_PRODUCTOS_COLUMNS, message),
            )

        productos = neo4j_data.get("productos_por_evento", [])

        return (
            bar_figure(
                productos,
                "producto_id",
                "total_eventos",
                "Productos por tipo de evento",
                "Producto",
                "Eventos",
            ),
            data_table(productos, NEO4J_PRODUCTOS_COLUMNS),
        )

    @dashboard_app.callback(
        Output("neo4j-usuarios-producto-status", "children"),
        Output("neo4j-usuarios-producto-table", "children"),
        Input("neo4j-producto-evento-button", "n_clicks"),
        State("neo4j-producto-evento-input", "value"),
        State("neo4j-producto-evento-dropdown", "value"),
        prevent_initial_call=True,
    )
    def buscar_usuarios_neo4j_por_producto(_, producto_id, tipo_evento):
        data = get_dashboard_data(
            neo4j_producto_id=producto_id,
            neo4j_producto_evento=tipo_evento,
        )
        neo4j_data = data.get("neo4j", {})

        if normalize_status(neo4j_data) != "ok":
            message = neo4j_data.get("error") or neo4j_data.get("message") or "Error en Neo4j"
            return message, data_table([], NEO4J_USUARIOS_PRODUCTO_COLUMNS, message)

        rows = neo4j_data.get("usuarios_por_producto_evento", [])
        context = neo4j_data.get("usuarios_producto_evento_context", {})
        status = (
            f"Producto: {context.get('producto_id') or 'sin resultados'} - "
            f"Evento: {context.get('tipo_evento') or tipo_evento}"
        )

        return status, data_table(rows, NEO4J_USUARIOS_PRODUCTO_COLUMNS)

    @dashboard_app.callback(
        Output("categoria-id-result", "children"),
        Input("buscar-categoria-button", "n_clicks"),
        State("categoria-id-input", "value"),
    )
    def buscar_categoria(_, categoria_id):
        return query_mongo_document(
            query_categoria_por_id,
            categoria_id,
            "No se encontro una categoria con ese ID.",
        )

    @dashboard_app.callback(
        Output("producto-id-result", "children"),
        Input("buscar-producto-button", "n_clicks"),
        State("producto-id-input", "value"),
    )
    def buscar_producto(_, producto_id):
        return query_mongo_document(
            query_producto_por_id,
            producto_id,
            "No se encontro un producto con ese ID.",
        )

    @dashboard_app.callback(
        Output("usuario-id-result", "children"),
        Input("buscar-usuario-button", "n_clicks"),
        State("usuario-id-input", "value"),
    )
    def buscar_usuario(_, usuario_id):
        return query_mongo_document(
            query_usuario_por_id,
            usuario_id,
            "No se encontro un usuario con ese ID.",
        )

    @dashboard_app.callback(
        Output("mongo-upsert-result", "children"),
        Input("mongo-upsert-button", "n_clicks"),
        State("mongo-upsert-producto-id", "value"),
        State("mongo-upsert-nombre", "value"),
        State("mongo-upsert-categoria-id", "value"),
        State("mongo-upsert-marca", "value"),
        State("mongo-upsert-precio", "value"),
        State("mongo-upsert-stock", "value"),
        prevent_initial_call=True,
    )
    def crud_mongo_upsert(_, producto_id, nombre, categoria_id, marca, precio, stock):
        return run_crud_operation(
            mongo_upsert_product,
            producto_id,
            nombre,
            categoria_id,
            marca,
            precio,
            stock,
        )

    @dashboard_app.callback(
        Output("mongo-delete-result", "children"),
        Input("mongo-delete-button", "n_clicks"),
        State("mongo-delete-producto-id", "value"),
        prevent_initial_call=True,
    )
    def crud_mongo_delete(_, producto_id):
        return run_crud_operation(mongo_delete_product, producto_id)

    @dashboard_app.callback(
        Output("cassandra-upsert-result", "children"),
        Output("cassandra-delete-result", "children"),
        Output("cassandra-crud-refresh-token", "data"),
        Input("cassandra-upsert-button", "n_clicks"),
        Input("cassandra-delete-button", "n_clicks"),
        State("cassandra-fecha", "value"),
        State("cassandra-producto-id", "value"),
        State("cassandra-categoria-id", "value"),
        State("cassandra-total-eventos", "value"),
        State("cassandra-total-vistas", "value"),
        State("cassandra-total-clicks", "value"),
        State("cassandra-total-busquedas", "value"),
        State("cassandra-total-favoritos", "value"),
        State("cassandra-total-compras", "value"),
        State("cassandra-score", "value"),
        State("cassandra-delete-fecha", "value"),
        State("cassandra-delete-producto-id", "value"),
        State("cassandra-crud-refresh-token", "data"),
        prevent_initial_call=True,
    )
    def crud_cassandra(
        _upsert_clicks,
        _delete_clicks,
        fecha,
        producto_id,
        categoria_id,
        total_eventos,
        total_vistas,
        total_clicks,
        total_busquedas,
        total_favoritos,
        total_compras,
        score,
        delete_fecha,
        delete_producto_id,
        refresh_token,
    ):
        triggered = callback_context.triggered[0]["prop_id"].split(".")[0]

        if triggered == "cassandra-upsert-button":
            result_view, result = execute_crud_operation(
                cassandra_upsert_daily_summary,
                fecha,
                producto_id,
                categoria_id,
                total_eventos,
                total_vistas,
                total_clicks,
                total_busquedas,
                total_favoritos,
                total_compras,
                score,
            )
            refresh = (
                next_cassandra_refresh_token(refresh_token, fecha)
                if crud_result_is_verified(result)
                else no_update
            )
            return result_view, no_update, refresh

        if triggered == "cassandra-delete-button":
            result_view, result = execute_crud_operation(
                cassandra_delete_daily_summary,
                delete_fecha,
                delete_producto_id,
            )
            refresh = (
                next_cassandra_refresh_token(refresh_token, delete_fecha)
                if crud_result_is_verified(result)
                else no_update
            )
            return no_update, result_view, refresh

        return no_update, no_update, no_update

    @dashboard_app.callback(
        Output("redis-upsert-result", "children"),
        Output("redis-delete-result", "children"),
        Output("redis-crud-refresh-token", "data"),
        Input("redis-upsert-button", "n_clicks"),
        Input("redis-delete-button", "n_clicks"),
        State("redis-producto-id", "value"),
        State("redis-categoria-id", "value"),
        State("redis-score", "value"),
        State("redis-delete-producto-id", "value"),
        State("redis-crud-refresh-token", "data"),
        prevent_initial_call=True,
    )
    def crud_redis(
        _upsert_clicks,
        _delete_clicks,
        producto_id,
        categoria_id,
        score,
        delete_producto_id,
        refresh_token,
    ):
        triggered = callback_context.triggered[0]["prop_id"].split(".")[0]

        if triggered == "redis-upsert-button":
            result_view, result = execute_crud_operation(
                redis_upsert_global_score,
                producto_id,
                score,
                categoria_id,
            )
            refresh = (
                next_redis_refresh_token(refresh_token)
                if crud_result_is_verified(result)
                else no_update
            )
            return result_view, no_update, refresh

        if triggered == "redis-delete-button":
            result_view, result = execute_crud_operation(
                redis_delete_global_score,
                delete_producto_id,
            )
            refresh = (
                next_redis_refresh_token(refresh_token)
                if crud_result_is_verified(result)
                else no_update
            )
            return no_update, result_view, refresh

        return no_update, no_update, no_update

    @dashboard_app.callback(
        Output("neo4j-upsert-result", "children"),
        Input("neo4j-upsert-button", "n_clicks"),
        State("neo4j-upsert-usuario-id", "value"),
        State("neo4j-upsert-producto-id", "value"),
        State("neo4j-upsert-tipo-evento", "value"),
        prevent_initial_call=True,
    )
    def crud_neo4j_upsert(_, usuario_id, producto_id, tipo_evento):
        return run_crud_operation(
            neo4j_upsert_user_event,
            usuario_id,
            producto_id,
            tipo_evento,
        )

    @dashboard_app.callback(
        Output("neo4j-delete-result", "children"),
        Input("neo4j-delete-button", "n_clicks"),
        State("neo4j-delete-usuario-id", "value"),
        State("neo4j-delete-producto-id", "value"),
        State("neo4j-delete-tipo-evento", "value"),
        prevent_initial_call=True,
    )
    def crud_neo4j_delete(_, usuario_id, producto_id, tipo_evento):
        return run_crud_operation(
            neo4j_delete_user_event,
            usuario_id,
            producto_id,
            tipo_evento,
        )

    return dashboard_app


app = create_dashboard_app()
server = app.server


def run_dashboard(host="127.0.0.1", port=8050, debug=False):
    """
    Levanta el dashboard web del proyecto.
    """

    print(f"Dashboard disponible en http://{host}:{port}")

    if hasattr(app, "run"):
        app.run(host=host, port=port, debug=debug)
    else:
        app.run_server(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_dashboard(debug=True)
