import csv
from decimal import Decimal
from io import StringIO
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Compra, CompraItem, Mercado, Produto

# Fatores de conversão para normalizar unidades (espelho do schemas.py).
_FATORES_CONVERSAO: dict[str, Decimal] = {
    "kg": Decimal("1"),
    "g": Decimal("0.001"),
    "l": Decimal("1"),
    "ml": Decimal("0.001"),
    "un": Decimal("1"),
}

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(tags=["Frontend"])

@router.get("/", response_class=HTMLResponse)
async def dashboard_view(request: Request, db: Session = Depends(get_db)):
    """Renderiza o Dashboard Interativo (KPIs, Gráficos, Outliers)."""
    # Para o dashboard, não passamos todos os objetos pesados, o frontend
    # fará fetch() via API, mas passamos a contagem para os KPIs rápidos.
    total_compras = db.query(Compra).count()
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"total_compras": total_compras}
    )

@router.get("/compras/novo", response_class=HTMLResponse)
async def nova_compra_view(request: Request, db: Session = Depends(get_db)):
    """Renderiza a Bancada de Lançamento (Formulário dinâmico)."""
    mercados = db.query(Mercado).all()
    produtos = db.query(Produto).all()
    
    # Extraindo listas únicas para o Autocomplete (datalist)
    tipos_unicos = sorted(list(set([p.tipo for p in produtos if p.tipo])))
    subtipos_unicos = sorted(list(set([p.subtipo for p in produtos if p.subtipo])))
    marcas_unicas = sorted(list(set([p.marca for p in produtos if p.marca])))
    categorias_unicas = sorted(list(set([p.categoria for p in produtos if p.categoria])))
    
    return templates.TemplateResponse(
        request=request,
        name="entrada_dados.html",
        context={
            "mercados": mercados,
            "produtos": produtos,
            "tipos": tipos_unicos,
            "subtipos": subtipos_unicos,
            "marcas": marcas_unicas,
            "categorias": categorias_unicas
        }
    )

@router.get("/historico", response_class=HTMLResponse)
async def historico_view(request: Request):
    """Renderiza a tabela de histórico de compras (alimentada via JS)."""
    return templates.TemplateResponse(
        request=request,
        name="historico.html",
        context={}
    )

@router.get("/config", response_class=HTMLResponse)
async def config_view(request: Request, db: Session = Depends(get_db)):
    """Renderiza a tela de gerenciamento de Cadastros."""
    mercados = db.query(Mercado).all()
    produtos = db.query(Produto).all()
    return templates.TemplateResponse(
        request=request,
        name="config.html",
        context={
            "mercados": mercados,
            "produtos": produtos
        }
    )

@router.get("/api/export/csv", response_class=PlainTextResponse)
async def export_csv(db: Session = Depends(get_db)):
    """Gera um arquivo CSV com o histórico completo de itens comprados."""
    itens = (
        db.query(CompraItem)
        .options(
            selectinload(CompraItem.compra).selectinload(Compra.mercado),
            selectinload(CompraItem.produto)
        )
        .all()
    )
    
    output = StringIO()
    writer = csv.writer(output, delimiter=";", lineterminator="\n")
    
    # Header
    writer.writerow([
        "Data Compra", "Mercado", "Tipo Mercado", "Cidade", "Estado",
        "Tipo Produto", "Subtipo Produto", "Marca", "Categoria",
        "Conteudo Embalagem", "Unidade Medida",
        "Qtd Embalagens", "Preco Pago", "Preco Unid. Padrao (Kg/L/Un)",
        "NF-e", "Observacoes",
        "Is Promoção", "Is Cupom", "Is Fidelidade", "Is Validade Proxima",
        "Fonte Dado"
    ])
    
    for item in itens:
        # Calcular preço por unidade padrão
        preco_unitario_padrao = Decimal("0.00")
        if item.produto:
            fator = _FATORES_CONVERSAO.get(item.produto.unidade_medida, Decimal("1"))
            conteudo_padrao = item.produto.conteudo_embalagem * fator
            if conteudo_padrao > 0:
                preco_unitario_padrao = (item.preco_pago / conteudo_padrao).quantize(Decimal("0.01"))
        
        writer.writerow([
            item.compra.data.isoformat() if item.compra else "",
            item.compra.mercado.nome if item.compra and item.compra.mercado else "",
            item.compra.mercado.tipo if item.compra and item.compra.mercado else "",
            item.compra.mercado.cidade if item.compra and item.compra.mercado else "",
            item.compra.mercado.estado if item.compra and item.compra.mercado else "",
            item.produto.tipo if item.produto else "",
            item.produto.subtipo if item.produto and item.produto.subtipo else "",
            item.produto.marca if item.produto else "",
            item.produto.categoria if item.produto else "",
            float(item.produto.conteudo_embalagem) if item.produto else "",
            item.produto.unidade_medida if item.produto else "",
            float(item.quantidade),
            float(item.preco_pago),
            float(preco_unitario_padrao),
            item.compra.nfe if item.compra and item.compra.nfe else "",
            item.compra.observacoes if item.compra and item.compra.observacoes else "",
            "Sim" if item.is_promocao else "Não",
            "Sim" if item.is_cupom else "Não",
            "Sim" if item.is_fidelidade else "Não",
            "Sim" if item.is_validade_proxima else "Não",
            item.fonte_dado
        ])
        
    response = PlainTextResponse(output.getvalue())
    response.headers["Content-Disposition"] = 'attachment; filename="historico_compras.csv"'
    return response
