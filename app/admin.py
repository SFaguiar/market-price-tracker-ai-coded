import os
from sqladmin import ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from app.models import Rede, Mercado, Produto, Compra, CompraItem

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

class RedeAdmin(ModelView, model=Rede):
    column_list = [Rede.id, Rede.nome]
    column_searchable_list = [Rede.nome]
    column_details_list = [Rede.id, Rede.nome, Rede.mercados]
    name = "Rede"
    name_plural = "Redes"
    icon = "fa-solid fa-sitemap"

class MercadoAdmin(ModelView, model=Mercado):
    column_list = [Mercado.id, Mercado.nome, Mercado.rede, Mercado.tipo, Mercado.cidade, Mercado.estado]
    column_searchable_list = [Mercado.nome, Mercado.tipo, Mercado.cidade, Mercado.estado]
    column_details_list = [
        Mercado.id, Mercado.nome, Mercado.rede, Mercado.tipo,
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

import json
from fastapi import Request
from sqlalchemy import select
from app.database import SessionLocal

class BulkImportView(BaseView):
    name = "Importação em Massa"
    icon = "fa-solid fa-cloud-arrow-up"

    @expose("/import", methods=["GET"])
    async def import_page_get(self, request: Request):
        return await self.templates.TemplateResponse(
            request,
            "import_admin.html",
            context={"message": None}
        )

    @expose("/import", methods=["POST"])
    async def import_page_post(self, request: Request):
        form = await request.form()
        json_text = form.get("json_data", "")
        entidade = form.get("entidade", "")

        try:
            dados = json.loads(json_text)
        except json.JSONDecodeError as e:
            return await self.templates.TemplateResponse(
                request,
                "import_admin.html",
                context={"message": {"type": "error", "text": f"Erro de formatação no JSON: {e}"}}
            )
        
        if not isinstance(dados, list):
            if entidade == "compras" and isinstance(dados, dict):
                dados = [dados]
            else:
                return await self.templates.TemplateResponse(
                    request,
                    "import_admin.html",
                    context={"message": {"type": "error", "text": "O JSON deve ser uma lista (array) de objetos."}}
                )

        inseridos = 0
        ignorados = 0

        with SessionLocal() as db:
            if entidade == "produtos":
                # Lógica de importação de Produtos
                existentes = db.execute(select(Produto)).scalars().all()
                set_existentes = set(
                    (
                        p.tipo.lower(),
                        p.subtipo.lower() if p.subtipo else "",
                        p.marca.lower(),
                        float(p.conteudo_embalagem),
                        p.unidade_medida.lower()
                    ) for p in existentes
                )

                for item in dados:
                    tipo = item.get("tipo")
                    subtipo = item.get("subtipo")
                    marca = item.get("marca")
                    categoria = item.get("categoria")
                    conteudo = item.get("conteudo_embalagem", item.get("conteudo_da_embalagem"))
                    unidade = item.get("unidade_medida", item.get("unidade", "")).lower()
                    
                    if unidade == "und":
                        unidade = "un"
                    
                    if not tipo or not marca or not categoria or conteudo is None or not unidade:
                        continue # Pula itens com dados faltando
                    
                    chave = (
                        tipo.lower(),
                        subtipo.lower() if subtipo else "",
                        marca.lower(),
                        float(conteudo),
                        unidade
                    )

                    if chave in set_existentes:
                        ignorados += 1
                        continue

                    db.add(Produto(
                        tipo=tipo, subtipo=subtipo, marca=marca,
                        categoria=categoria, conteudo_embalagem=conteudo, unidade_medida=unidade
                    ))
                    set_existentes.add(chave)
                    inseridos += 1
            
            elif entidade == "mercados":
                # Lógica de importação de Mercados
                existentes = db.execute(select(Mercado)).scalars().all()
                set_existentes = set(m.nome.lower() for m in existentes)

                for item in dados:
                    nome = item.get("nome")
                    tipo = item.get("tipo")
                    
                    if not nome or not tipo:
                        continue # Pula itens inválidos
                    
                    if nome.lower() in set_existentes:
                        ignorados += 1
                        continue
                    
                    db.add(Mercado(
                        nome=nome,
                        tipo=tipo,
                        endereco=item.get("endereco"),
                        cidade=item.get("cidade"),
                        estado=item.get("estado"),
                        latitude=item.get("latitude"),
                        longitude=item.get("longitude")
                    ))
                    set_existentes.add(nome.lower())
                    inseridos += 1
            elif entidade == "compras":
                import datetime
                
                existentes_mercados = db.execute(select(Mercado)).scalars().all()
                dict_mercados = {m.nome.lower(): m for m in existentes_mercados}
                
                existentes_produtos = db.execute(select(Produto)).scalars().all()
                dict_produtos = {
                    (
                        p.tipo.lower(),
                        p.subtipo.lower() if p.subtipo else "",
                        p.marca.lower(),
                        float(p.conteudo_embalagem),
                        p.unidade_medida.lower()
                    ): p for p in existentes_produtos
                }
                
                compras_inseridas = 0
                itens_inseridos = 0
                produtos_inseridos = 0
                mercados_inseridos = 0

                for compra_data in dados:
                    m_data = compra_data.get("mercado", {})
                    m_nome = m_data.get("nome")
                    if not m_nome:
                        continue
                    
                    m_key = m_nome.lower()
                    mercado_obj = dict_mercados.get(m_key)
                    if not mercado_obj:
                        mercado_obj = Mercado(
                            nome=m_nome,
                            tipo=m_data.get("tipo", "Desconhecido"),
                            endereco=m_data.get("endereco")
                        )
                        db.add(mercado_obj)
                        db.flush()
                        dict_mercados[m_key] = mercado_obj
                        mercados_inseridos += 1
                        
                    data_emissao_str = compra_data.get("data_emissao")
                    data_obj = datetime.date.today()
                    if data_emissao_str:
                        try:
                            data_part = data_emissao_str.split(" ")[0]
                            d, m, y = data_part.split("/")
                            data_obj = datetime.date(int(y), int(m), int(d))
                        except Exception:
                            pass
                            
                    nova_compra = Compra(
                        mercado_id=mercado_obj.id,
                        data=data_obj,
                        nfe=compra_data.get("nfe")
                    )
                    db.add(nova_compra)
                    db.flush()
                    compras_inseridas += 1
                    
                    itens_list = compra_data.get("itens", [])
                    for i_data in itens_list:
                        p_data = i_data.get("produto", {})
                        tipo = p_data.get("tipo")
                        marca = p_data.get("marca")
                        if not tipo or not marca:
                            continue
                            
                        subtipo = p_data.get("subtipo") or ""
                        conteudo = float(p_data.get("conteudo_embalagem") or 1)
                        unidade = (p_data.get("unidade_medida") or "un").lower()
                        if unidade == "und": unidade = "un"
                        
                        p_key = (tipo.lower(), subtipo.lower(), marca.lower(), conteudo, unidade)
                        
                        produto_obj = dict_produtos.get(p_key)
                        if not produto_obj:
                            produto_obj = Produto(
                                tipo=tipo,
                                subtipo=subtipo,
                                marca=marca,
                                categoria=p_data.get("categoria", "Geral"),
                                conteudo_embalagem=conteudo,
                                unidade_medida=unidade
                            )
                            db.add(produto_obj)
                            db.flush()
                            dict_produtos[p_key] = produto_obj
                            produtos_inseridos += 1
                            
                        novo_item = CompraItem(
                            compra_id=nova_compra.id,
                            produto_id=produto_obj.id,
                            preco_pago=float(i_data.get("valor_unitario", 0)),
                            quantidade=float(i_data.get("quantidade", 1)),
                            fonte_dado="cupom_fiscal"
                        )
                        db.add(novo_item)
                        itens_inseridos += 1
                
                db.commit()
                mensagem = f"Importação concluída! {compras_inseridas} compras com {itens_inseridos} itens inseridos. {mercados_inseridos} mercados criados e {produtos_inseridos} novos produtos registrados."
                return await self.templates.TemplateResponse(
                    request,
                    "import_admin.html",
                    context={"message": {"type": "success", "text": mensagem}}
                )
            else:
                return await self.templates.TemplateResponse(
                    request,
                    "import_admin.html",
                    context={"message": {"type": "error", "text": "Entidade inválida selecionada."}}
                )
            
            db.commit()

        return await self.templates.TemplateResponse(
            request,
            "import_admin.html",
            context={"message": {"type": "success", "text": f"Importação concluída! {inseridos} registros inseridos, {ignorados} duplicatas ignoradas."}}
        )

class NFEParserView(BaseView):
    name = "Extrator de NFC-e"
    icon = "fa-solid fa-file-invoice"

    @expose("/nfe-parser", methods=["GET"])
    async def nfe_parser_get(self, request: Request):
        return await self.templates.TemplateResponse(
            request,
            "nfe_parser_admin.html",
            context={"json_result": "", "error": None}
        )

    @expose("/nfe-parser", methods=["POST"])
    async def nfe_parser_post(self, request: Request):
        form = await request.form()
        html_content = form.get("html_data", "")

        if not html_content:
            return await self.templates.TemplateResponse(
                request,
                "nfe_parser_admin.html",
                context={"json_result": "", "error": "Nenhum HTML fornecido."}
            )

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extrair Mercado e Endereço
            header = soup.find('div', id='heading1')
            if not header:
                raise ValueError("Cabeçalho do Mercado não encontrado no HTML (id='heading1' ausente).")
            
            divs = header.find_all('div')
            nome_mercado = divs[0].text.strip() if len(divs) > 0 else "NOME DO MERCADO DESCONHECIDO"
            endereco = divs[2].text.strip().replace('\r', '').replace('\n', ' ') if len(divs) > 2 else ""
            # Limpar espaços duplos no endereço
            import re
            endereco = re.sub(r'\s+', ' ', endereco)

            # Extrair Data e Chave
            text_full = soup.get_text(separator=' ')
            chave_match = re.search(r'([\d]{4}\s[\d]{4}\s[\d]{4}\s[\d]{4}\s[\d]{4}\s[\d]{4}\s[\d]{4}\s[\d]{4}\s[\d]{4}\s[\d]{4}\s[\d]{4})', text_full)
            chave = chave_match.group(1).replace(' ', '') if chave_match else ""
            
            data_match = re.search(r'([\d]{2}/[\d]{2}/[\d]{4}\s[\d]{2}:[\d]{2}:[\d]{2})', text_full)
            data_emissao = data_match.group(1) if data_match else ""
            
            items = []
            
            ul_items = soup.find('div', id='collapse1')
            if ul_items:
                ul_list = ul_items.find('ul', class_='list-group')
                if ul_list:
                    li_items = ul_list.find_all('li', class_='list-group-item')
                    for li in li_items:
                        p_nome = li.find('p', class_='h6')
                        if not p_nome: continue
                        
                        nome_raw = p_nome.contents[0].strip() if p_nome.contents else ""
                        
                        span_dados = li.find('span', style="font-size:11px;")
                        if not span_dados: continue
                        
                        text_nodes = [t for t in span_dados.contents if isinstance(t, str) and t.strip()]
                        
                        qtde = 0.0
                        unidade = ""
                        vl_unit = 0.0
                        
                        if len(text_nodes) >= 3:
                            try:
                                qtde = float(text_nodes[0].strip().replace(',', '.'))
                                unidade = text_nodes[1].strip()
                                vl_unit = float(text_nodes[2].strip().replace(',', '.'))
                            except ValueError:
                                pass
                            
                        items.append({
                            "produto_bruto": nome_raw,
                            "quantidade": qtde,
                            "unidade": unidade,
                            "valor_unitario": vl_unit
                        })

            resultado = {
                "mercado": nome_mercado,
                "endereco": endereco,
                "chave_nfe": chave,
                "data_emissao": data_emissao,
                "itens": items
            }

            from fastapi.responses import JSONResponse
            # Retorna um JSON diretamente para a chamada AJAX
            return JSONResponse(content=resultado)

        except Exception as e:
            from fastapi.responses import JSONResponse
            return JSONResponse(content={"error": f"Erro ao processar HTML: {str(e)}"}, status_code=400)

class DeduplicationView(BaseView):
    name = "Saneamento (Deduplicação)"
    icon = "fa-solid fa-broom"

    @expose("/saneamento", methods=["GET"])
    async def deduplication_page(self, request: Request):
        return await self.templates.TemplateResponse(
            request,
            "dedup_admin.html"
        )
