"""
Rotas CRUD para a entidade Produto.

Endpoints:
    POST   /produtos/       -> Cria um novo produto.
    GET    /produtos/       -> Lista todos os produtos (filtros opcionais).
    GET    /produtos/{id}   -> Retorna um produto específico.
    DELETE /produtos/{id}   -> Remove um produto.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Produto
from app.schemas import ProdutoCreate, ProdutoResponse

router = APIRouter(prefix="/produtos", tags=["Produtos"])


@router.post(
    "/",
    response_model=ProdutoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um novo produto",
)
def criar_produto(
    produto: ProdutoCreate, db: Session = Depends(get_db)
) -> Produto:
    """Persiste um novo produto no catálogo do sistema.

    Args:
        produto: Payload validado com tipo, subtipo, marca, categoria,
                 conteudo_embalagem e unidade_medida.
        db: Sessão do banco injetada via Depends.

    Returns:
        O produto recém-criado com seu ``id`` atribuído.
    """
    db_produto = Produto(**produto.model_dump())
    db.add(db_produto)
    db.commit()
    db.refresh(db_produto)
    return db_produto


@router.get(
    "/",
    response_model=List[ProdutoResponse],
    summary="Lista todos os produtos",
)
def listar_produtos(
    tipo: Optional[str] = Query(
        default=None,
        description="Filtrar por tipo genérico do produto (ex: 'Arroz', 'Feijão').",
    ),
    subtipo: Optional[str] = Query(
        default=None,
        description="Filtrar por subtipo do produto (ex: 'Integral', 'Carioca').",
    ),
    categoria: Optional[str] = Query(
        default=None,
        description="Filtrar por categoria (ex: 'Mercearia', 'Hortifrúti').",
    ),
    marca: Optional[str] = Query(
        default=None,
        description="Filtrar por marca (ex: 'Camil').",
    ),
    db: Session = Depends(get_db),
) -> list[Produto]:
    """Retorna a lista completa de produtos cadastrados.

    Args:
        tipo: Filtro opcional pelo tipo genérico do produto.
        subtipo: Filtro opcional pelo subtipo do produto.
        categoria: Filtro opcional pela categoria do produto.
        marca: Filtro opcional pela marca do produto.
        db: Sessão do banco injetada via Depends.

    Returns:
        Lista de produtos, opcionalmente filtrada.
    """
    query = db.query(Produto)
    if tipo is not None:
        query = query.filter(Produto.tipo == tipo)
    if subtipo is not None:
        query = query.filter(Produto.subtipo == subtipo)
    if categoria is not None:
        query = query.filter(Produto.categoria == categoria)
    if marca is not None:
        query = query.filter(Produto.marca == marca)
    return query.all()


@router.get(
    "/{produto_id}",
    response_model=ProdutoResponse,
    summary="Retorna um produto específico",
)
def obter_produto(produto_id: int, db: Session = Depends(get_db)) -> Produto:
    """Busca um produto pelo seu identificador único.

    Args:
        produto_id: ID do produto desejado.
        db: Sessão do banco injetada via Depends.

    Returns:
        O produto correspondente ao ID.

    Raises:
        HTTPException: 404 se o produto não for encontrado.
    """
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if produto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Produto com id={produto_id} não encontrado.",
        )
    return produto


@router.delete(
    "/{produto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove um produto",
)
def deletar_produto(
    produto_id: int, db: Session = Depends(get_db)
) -> None:
    """Remove um produto do catálogo.

    Args:
        produto_id: ID do produto a ser removido.
        db: Sessão do banco injetada via Depends.

    Raises:
        HTTPException: 404 se o produto não for encontrado.
    """
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if produto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Produto com id={produto_id} não encontrado.",
        )
    db.delete(produto)
    db.commit()
