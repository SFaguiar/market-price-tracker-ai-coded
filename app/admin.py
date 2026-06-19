import os
from sqladmin import ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from app.models import Mercado, Produto, Compra, CompraItem

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        # Verifica as credenciais lidas do .env
        expected_user = os.getenv("ADMIN_USER", "admin")
        expected_pass = os.getenv("ADMIN_PASSWORD", "admin123")

        if username == expected_user and password == expected_pass:
            # Login successful
            request.session.update({"token": "admin_session_token"})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        # Limpar o token da sessão
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        # Retorna True se a sessão for válida
        token = request.session.get("token")
        if not token:
            return False
        return True

# Views do Administrador

class MercadoAdmin(ModelView, model=Mercado):
    column_list = [Mercado.id, Mercado.nome, Mercado.tipo, Mercado.cidade, Mercado.estado]
    column_searchable_list = [Mercado.nome, Mercado.tipo, Mercado.cidade, Mercado.estado]
    column_details_list = [
        Mercado.id, Mercado.nome, Mercado.tipo,
        Mercado.endereco, Mercado.cidade, Mercado.estado,
        Mercado.latitude, Mercado.longitude
    ]
    name = "Mercado"
    name_plural = "Mercados"
    icon = "fa-solid fa-store"

class ProdutoAdmin(ModelView, model=Produto):
    column_list = [
        Produto.id, Produto.tipo, Produto.subtipo,
        Produto.marca, Produto.categoria,
        Produto.conteudo_embalagem, Produto.unidade_medida
    ]
    column_searchable_list = [Produto.tipo, Produto.subtipo, Produto.marca, Produto.categoria]
    name = "Produto"
    name_plural = "Produtos"
    icon = "fa-solid fa-box"

class CompraAdmin(ModelView, model=Compra):
    column_list = [Compra.id, Compra.data, Compra.mercado_id, Compra.mercado, Compra.nfe]
    column_searchable_list = [Compra.data, Compra.nfe]
    column_details_list = [
        Compra.id, Compra.data, Compra.mercado,
        Compra.nfe, Compra.observacoes
    ]
    name = "Compra"
    name_plural = "Compras"
    icon = "fa-solid fa-shopping-cart"

class CompraItemAdmin(ModelView, model=CompraItem):
    column_list = [
        CompraItem.id, 
        CompraItem.produto, 
        CompraItem.quantidade, 
        CompraItem.preco_pago,
        CompraItem.is_promocao
    ]
    name = "Item da Compra"
    name_plural = "Itens da Compra"
    icon = "fa-solid fa-receipt"

from sqladmin import BaseView, expose
from sqlalchemy import inspect
from app.database import engine

class SchemaView(BaseView):
    name = "Dicionário de Dados"
    icon = "fa-solid fa-database"

    @expose("/schema", methods=["GET"])
    async def schema_page(self, request):
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        schema_info = {}
        for table_name in table_names:
            columns = inspector.get_columns(table_name)
            pks = inspector.get_pk_constraint(table_name).get("constrained_columns", [])
            fks = inspector.get_foreign_keys(table_name)
            
            col_list = []
            for col in columns:
                col_name = col["name"]
                is_pk = col_name in pks
                
                fk_target = None
                for fk in fks:
                    if col_name in fk["constrained_columns"]:
                        idx = fk["constrained_columns"].index(col_name)
                        fk_target = f"{fk['referred_table']}.{fk['referred_columns'][idx]}"
                        break
                
                col_list.append({
                    "name": col_name,
                    "type": str(col["type"]),
                    "nullable": col["nullable"],
                    "primary_key": is_pk,
                    "foreign_key": fk_target
                })
                
            schema_info[table_name] = col_list
            
        return await self.templates.TemplateResponse(
            request,
            "schema_admin.html",
            context={"schema_info": schema_info}
        )
