"""
Ponto de entrada da aplicação Market Price Tracker.

Responsável por:
- Instanciar a aplicação FastAPI.
- Configurar o ciclo de vida (lifespan) para criação automática das tabelas.
- Registrar os roteadores CRUD de mercados, produtos e compras.
- Expor o endpoint de verificação de integridade (health check).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routes import compras, mercados, produtos, web, redes, saneamento, dashboard

from sqladmin import Admin
from app.admin import AdminAuth, RedeAdmin, MercadoAdmin, ProdutoAdmin, CompraAdmin, CompraItemAdmin, SchemaView, BulkImportView, NFEParserView, DeduplicationView


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciador de contexto do ciclo de vida da aplicação.

    No startup, cria todas as tabelas definidas nos modelos ORM caso
    elas ainda não existam no banco de dados SQLite. Isso garante que
    o diretório ``data/`` e o arquivo ``precos.db`` sejam gerados
    automaticamente na primeira execução.
    """
    # Importar models para garantir que Base.metadata conheça todas as tabelas.
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Market Price Tracker",
    description=(
        "Sistema de rastreamento de preços domésticos e análise de "
        "sazonalidade. Converte o caos das compras em dados estruturados "
        "para decisões estratégicas de consumo."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Admin UI
# ---------------------------------------------------------------------------

import os
secret_key = os.getenv("SECRET_KEY", "fallback_secret_key_if_missing")
authentication_backend = AdminAuth(secret_key=secret_key)

admin = Admin(app, engine, authentication_backend=authentication_backend, templates_dir="app/templates")
admin.add_view(RedeAdmin)
admin.add_view(MercadoAdmin)
admin.add_view(ProdutoAdmin)
admin.add_view(CompraAdmin)
admin.add_view(CompraItemAdmin)
admin.add_view(SchemaView)
admin.add_view(BulkImportView)
admin.add_view(NFEParserView)
admin.add_view(DeduplicationView)

# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["Health"])
async def health_check():
    """Verifica se a API está online."""
    return {"status": "healthy"}


app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ---------------------------------------------------------------------------
# Registro de Roteadores
# ---------------------------------------------------------------------------

app.include_router(web.router)
app.include_router(redes.router)
app.include_router(mercados.router)
app.include_router(produtos.router)
app.include_router(compras.router)
app.include_router(saneamento.router)
app.include_router(dashboard.router)
