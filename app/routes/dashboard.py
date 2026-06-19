from decimal import Decimal
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.database import get_db
from app.models import Mercado, Compra, CompraItem, Produto

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

CESTA_SIMPLES = [
    "arroz", "feijão", "macarrão", "açúcar", "sal", "óleo", "café", "farinha", "leite"
]

CESTA_COMPLETA = CESTA_SIMPLES + [
    "carne", "frango", "ovo", "queijo", "pão", "sabão", "detergente", "creme dental", "papel higiênico", "sabonete"
]

_FATORES_CONVERSAO: dict[str, Decimal] = {
    "kg": Decimal("1"),
    "g": Decimal("0.001"),
    "l": Decimal("1"),
    "ml": Decimal("0.001"),
    "un": Decimal("1"),
}

def calcular_preco_padrao(item: CompraItem) -> float:
    if not item.produto:
        return float(item.preco_pago)
    
    fator = _FATORES_CONVERSAO.get(item.produto.unidade_medida.lower(), Decimal("1"))
    conteudo_padrao = item.produto.conteudo_embalagem * fator
    if conteudo_padrao > 0:
        return float((item.preco_pago / conteudo_padrao).quantize(Decimal("0.01")))
    return float(item.preco_pago)

@router.get("/cestas")
def get_ranking_cestas(db: Session = Depends(get_db)):
    mercados = db.query(Mercado).all()
    ranking_simples = []
    ranking_completo = []

    for mercado in mercados:
        # Busca a última compra desse mercado
        ultima_compra = db.query(Compra).filter(Compra.mercado_id == mercado.id).order_by(desc(Compra.data)).first()
        
        if not ultima_compra:
            continue
            
        itens_mercado = (
            db.query(CompraItem)
            .join(Compra)
            .join(Produto)
            .filter(Compra.mercado_id == mercado.id)
            .order_by(desc(Compra.data))
            .all()
        )
        
        # Guarda o menor preço padrão recente para um tipo de produto
        precos_por_tipo = {}
        for item in itens_mercado:
            tipo_lower = item.produto.tipo.lower()
            preco_padrao = calcular_preco_padrao(item)
            
            if tipo_lower not in precos_por_tipo:
                precos_por_tipo[tipo_lower] = preco_padrao
            else:
                if item.compra.data >= ultima_compra.data:
                    precos_por_tipo[tipo_lower] = min(precos_por_tipo[tipo_lower], preco_padrao)

        # Calcula Simples
        preco_simples = 0.0
        faltantes_simples = []
        for item_cesta in CESTA_SIMPLES:
            encontrado = False
            for k, v in precos_por_tipo.items():
                if item_cesta in k:
                    preco_simples += v
                    encontrado = True
                    break
            if not encontrado:
                faltantes_simples.append(item_cesta)

        # Calcula Completa
        preco_completo = 0.0
        faltantes_completo = []
        for item_cesta in CESTA_COMPLETA:
            encontrado = False
            for k, v in precos_por_tipo.items():
                if item_cesta in k:
                    preco_completo += v
                    encontrado = True
                    break
            if not encontrado:
                faltantes_completo.append(item_cesta)

        ranking_simples.append({
            "mercado": mercado.nome,
            "preco_total": round(preco_simples, 2),
            "status": "Incompleta" if faltantes_simples else "Completa",
            "faltantes": faltantes_simples,
            "id": mercado.id
        })

        ranking_completo.append({
            "mercado": mercado.nome,
            "preco_total": round(preco_completo, 2),
            "status": "Incompleta" if faltantes_completo else "Completa",
            "faltantes": faltantes_completo,
            "id": mercado.id
        })

    ranking_simples.sort(key=lambda x: (len(x["faltantes"]), x["preco_total"]))
    ranking_completo.sort(key=lambda x: (len(x["faltantes"]), x["preco_total"]))

    return {
        "cesta_simples": ranking_simples,
        "cesta_completa": ranking_completo
    }


@router.get("/search")
def search_prices(query: str = Query(..., min_length=2), db: Session = Depends(get_db)):
    """Busca o preço de um produto em diferentes mercados."""
    query_lower = query.lower()
    
    itens = (
        db.query(CompraItem)
        .join(Compra)
        .join(Produto)
        .filter(
            Produto.tipo.ilike(f"%{query_lower}%") | Produto.marca.ilike(f"%{query_lower}%")
        )
        .order_by(desc(Compra.data))
        .all()
    )
    
    resultados_mercados = {}
    
    for item in itens:
        m_id = item.compra.mercado_id
        if m_id not in resultados_mercados:
            resultados_mercados[m_id] = {
                "mercado": item.compra.mercado.nome,
                "preco_padrao": calcular_preco_padrao(item),
                "data": item.compra.data.strftime("%d/%m/%Y"),
                "produto_str": f"{item.produto.tipo} {item.produto.subtipo or ''} - {item.produto.marca}",
                "unidade": "1 " + ("Kg" if item.produto.unidade_medida in ['kg', 'g'] else "L" if item.produto.unidade_medida in ['l', 'ml'] else "Un")
            }
            
    lista_res = list(resultados_mercados.values())
    lista_res.sort(key=lambda x: x["preco_padrao"])
    
    return {"resultados": lista_res}
