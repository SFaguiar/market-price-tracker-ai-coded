from collections import defaultdict
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Produto, CompraItem

router = APIRouter(prefix="/saneamento", tags=["Saneamento"])

class MesclarRequest(BaseModel):
    mestre_id: int
    duplicados_ids: List[int]
    novo_tipo: Optional[str] = None
    novo_subtipo: Optional[str] = None
    nova_marca: Optional[str] = None

def gerar_assinatura(p: Produto) -> str:
    sub = p.subtipo if p.subtipo else ""
    # Junta as strings para análise de similaridade textual
    return f"{p.tipo} {sub} {p.marca} {float(p.conteudo_embalagem)}".lower().strip()

@router.get("/duplicados")
def listar_duplicados(db: Session = Depends(get_db)):
    produtos = db.query(Produto).all()
    
    # Agrupar apenas por unidade_medida (Cross-Categoria)
    blocos = defaultdict(list)
    for p in produtos:
        blocos[p.unidade_medida.lower()].append(p)
        
    clusters = []
    produtos_visitados = set()
    
    for chave_bloco, lista_prods in blocos.items():
        if len(lista_prods) < 2:
            continue
            
        for i, p1 in enumerate(lista_prods):
            if p1.id in produtos_visitados:
                continue
                
            cluster_atual = [p1]
            assinatura1 = gerar_assinatura(p1)
            
            for j in range(i + 1, len(lista_prods)):
                p2 = lista_prods[j]
                if p2.id in produtos_visitados:
                    continue
                    
                assinatura2 = gerar_assinatura(p2)
                
                # Checar similaridade (0.0 a 1.0)
                ratio = SequenceMatcher(None, assinatura1, assinatura2).ratio()
                
                # Threshold empírico de 82% de similaridade
                if ratio >= 0.82:
                    cluster_atual.append(p2)
                    
            if len(cluster_atual) > 1:
                clusters.append({
                    "id_cluster": f"cluster_{p1.id}",
                    "unidade_medida": p1.unidade_medida,
                    "produtos": [
                        {
                            "id": p.id,
                            "tipo": p.tipo,
                            "subtipo": p.subtipo,
                            "marca": p.marca,
                            "embalagem": f"{float(p.conteudo_embalagem)}{p.unidade_medida}",
                            "assinatura": gerar_assinatura(p)
                        } for p in cluster_atual
                    ]
                })
                for p in cluster_atual:
                    produtos_visitados.add(p.id)
                    
    return {"clusters": clusters}

@router.post("/mesclar")
def mesclar_produtos(req: MesclarRequest, db: Session = Depends(get_db)):
    if req.mestre_id in req.duplicados_ids:
        raise HTTPException(status_code=400, detail="O produto mestre não pode estar na lista de produtos para deletar.")
        
    mestre = db.query(Produto).filter(Produto.id == req.mestre_id).first()
    if not mestre:
        raise HTTPException(status_code=404, detail="Produto mestre não encontrado.")
        
    # Valida se os duplicados existem
    duplicados = db.query(Produto).filter(Produto.id.in_(req.duplicados_ids)).all()
    if len(duplicados) != len(req.duplicados_ids):
        raise HTTPException(status_code=404, detail="Um ou mais produtos duplicados não foram encontrados no banco.")
        
    try:
        # 0. Atualizar atributos do Mestre (Edição Inline)
        if req.novo_tipo is not None and req.novo_tipo.strip():
            mestre.tipo = req.novo_tipo.strip()
        if req.novo_subtipo is not None:
            mestre.subtipo = req.novo_subtipo.strip() if req.novo_subtipo.strip() else None
        if req.nova_marca is not None and req.nova_marca.strip():
            mestre.marca = req.nova_marca.strip()

        # 1. Update Foreign Keys (Mover compras para o Mestre)
        db.query(CompraItem).filter(CompraItem.produto_id.in_(req.duplicados_ids)).update(
            {CompraItem.produto_id: req.mestre_id}, 
            synchronize_session=False
        )
        
        # 2. Deletar as vítimas
        db.query(Produto).filter(Produto.id.in_(req.duplicados_ids)).delete(
            synchronize_session=False
        )
        
        db.commit()
        return {"status": "success", "message": f"{len(req.duplicados_ids)} produtos mesclados com sucesso sob o ID {req.mestre_id}."}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro crítico durante a mesclagem. Rollback executado: {str(e)}")
