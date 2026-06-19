"""
Rotas CRUD para a entidade Mercado.

Endpoints:
    POST   /mercados/       -> Cria um novo mercado.
    GET    /mercados/       -> Lista todos os mercados (filtro opcional por tipo).
    GET    /mercados/{id}   -> Retorna um mercado específico.
    DELETE /mercados/{id}   -> Remove um mercado.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Mercado
from app.schemas import MercadoCreate, MercadoResponse

router = APIRouter(prefix="/mercados", tags=["Mercados"])


@router.post(
    "/",
    response_model=MercadoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um novo mercado",
)
def criar_mercado(
    mercado: MercadoCreate, db: Session = Depends(get_db)
) -> Mercado:
    """Persiste um novo estabelecimento comercial no banco de dados.

    Args:
        mercado: Payload validado com nome e tipo do mercado.
        db: Sessão do banco injetada via Depends.

    Returns:
        O mercado recém-criado com seu ``id`` atribuído.
    """
    db_mercado = Mercado(**mercado.model_dump())
    db.add(db_mercado)
    db.commit()
    db.refresh(db_mercado)
    return db_mercado


@router.get(
    "/",
    response_model=List[MercadoResponse],
    summary="Lista todos os mercados",
)
def listar_mercados(
    tipo: Optional[str] = Query(
        default=None,
        description="Filtrar por tipo de mercado (ex: 'Atacado', 'Feira').",
    ),
    db: Session = Depends(get_db),
) -> list[Mercado]:
    """Retorna a lista completa de mercados cadastrados.

    Args:
        tipo: Filtro opcional pelo tipo de estabelecimento.
        db: Sessão do banco injetada via Depends.

    Returns:
        Lista de mercados, opcionalmente filtrada por tipo.
    """
    query = db.query(Mercado)
    if tipo is not None:
        query = query.filter(Mercado.tipo == tipo)
    return query.all()


@router.get(
    "/{mercado_id}",
    response_model=MercadoResponse,
    summary="Retorna um mercado específico",
)
def obter_mercado(mercado_id: int, db: Session = Depends(get_db)) -> Mercado:
    """Busca um mercado pelo seu identificador único.

    Args:
        mercado_id: ID do mercado desejado.
        db: Sessão do banco injetada via Depends.

    Returns:
        O mercado correspondente ao ID.

    Raises:
        HTTPException: 404 se o mercado não for encontrado.
    """
    mercado = db.query(Mercado).filter(Mercado.id == mercado_id).first()
    if mercado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mercado com id={mercado_id} não encontrado.",
        )
    return mercado


@router.delete(
    "/{mercado_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove um mercado",
)
def deletar_mercado(
    mercado_id: int, db: Session = Depends(get_db)
) -> None:
    """Remove um mercado e todas as suas compras associadas (cascade).

    Args:
        mercado_id: ID do mercado a ser removido.
        db: Sessão do banco injetada via Depends.

    Raises:
        HTTPException: 404 se o mercado não for encontrado.
    """
    mercado = db.query(Mercado).filter(Mercado.id == mercado_id).first()
    if mercado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mercado com id={mercado_id} não encontrado.",
        )
    db.delete(mercado)
    db.commit()
