"""
Rotas CRUD para a entidade Compra e seus itens.

Endpoints de Compra:
    POST   /compras/                    -> Cria compra com itens aninhados.
    GET    /compras/                    -> Lista compras (filtros avançados).
    GET    /compras/{id}               -> Retorna compra com itens detalhados.
    DELETE /compras/{id}               -> Remove compra e itens (cascade).

Endpoints de Itens individuais:
    POST   /compras/{compra_id}/itens/ -> Adiciona item a uma compra existente.
    DELETE /compras/itens/{item_id}    -> Remove um item individual.
"""

import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Compra, CompraItem, Mercado
from app.schemas import (
    CompraCreate,
    CompraItemCreate,
    CompraItemResponse,
    CompraResponse,
)

router = APIRouter(prefix="/compras", tags=["Compras"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _carregar_compra_completa(db: Session, compra_id: int) -> Compra:
    """Carrega uma compra com todos os relacionamentos (eager loading).

    Utiliza ``selectinload`` para evitar o problema N+1 de queries ao
    serializar o mercado e os itens com seus respectivos produtos.

    Args:
        db: Sessão ativa do banco de dados.
        compra_id: ID da compra a ser carregada.

    Returns:
        Instância de Compra com todos os relacionamentos carregados.

    Raises:
        HTTPException: 404 se a compra não for encontrada.
    """
    compra = (
        db.query(Compra)
        .options(
            selectinload(Compra.mercado),
            selectinload(Compra.itens).selectinload(CompraItem.produto),
        )
        .filter(Compra.id == compra_id)
        .first()
    )
    if compra is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compra com id={compra_id} não encontrada.",
        )
    return compra


# ---------------------------------------------------------------------------
# CRUD de Compra
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=CompraResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma nova compra com itens",
)
def criar_compra(
    compra: CompraCreate, db: Session = Depends(get_db)
) -> Compra:
    """Registra uma compra completa com todos os seus itens.

    Reflete a operação natural de registrar uma nota fiscal: o mercado,
    a data, NF-e, observações e todos os itens são persistidos em uma
    única transação atômica.

    Args:
        compra: Payload validado contendo mercado_id, data, nfe,
                observacoes e lista de itens.
        db: Sessão do banco injetada via Depends.

    Returns:
        A compra recém-criada com seus itens e relacionamentos.

    Raises:
        HTTPException: 404 se o mercado referenciado não existir.
    """
    # Validar existência do mercado referenciado.
    mercado = db.query(Mercado).filter(Mercado.id == compra.mercado_id).first()
    if mercado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mercado com id={compra.mercado_id} não encontrado.",
        )

    # Criar a compra pai.
    db_compra = Compra(
        mercado_id=compra.mercado_id,
        data=compra.data,
        nfe=compra.nfe,
        observacoes=compra.observacoes,
    )
    db.add(db_compra)
    db.flush()  # Gera o id da compra antes de criar os itens.

    # Criar os itens associados.
    for item_data in compra.itens:
        db_item = CompraItem(
            compra_id=db_compra.id,
            **item_data.model_dump(),
        )
        db.add(db_item)

    db.commit()

    # Recarregar com eager loading para serialização completa.
    return _carregar_compra_completa(db, db_compra.id)


@router.get(
    "/",
    response_model=List[CompraResponse],
    summary="Lista todas as compras",
)
def listar_compras(
    mercado_id: Optional[int] = Query(
        default=None,
        description="Filtrar por ID do mercado.",
    ),
    data_inicio: Optional[datetime.date] = Query(
        default=None,
        description="Data inicial do período (YYYY-MM-DD).",
    ),
    data_fim: Optional[datetime.date] = Query(
        default=None,
        description="Data final do período (YYYY-MM-DD).",
    ),
    dia_semana: Optional[int] = Query(
        default=None,
        ge=0,
        le=6,
        description=(
            "Filtrar por dia da semana (0=segunda, 6=domingo). "
            "Usa a função strftime do SQLite."
        ),
    ),
    is_cupom: Optional[bool] = Query(
        default=None,
        description=(
            "Filtrar compras que contenham (True) ou não (False) "
            "itens adquiridos com cupom."
        ),
    ),
    db: Session = Depends(get_db),
) -> list[Compra]:
    """Retorna a lista de compras com filtros avançados.

    Suporta filtragem por mercado, período de datas, dia da semana
    e presença de itens com cupom — permitindo análises de sazonalidade
    e controle de viés.

    Args:
        mercado_id: Filtrar por mercado específico.
        data_inicio: Limite inferior do período.
        data_fim: Limite superior do período.
        dia_semana: Dia da semana (0=seg, 6=dom) via strftime do SQLite.
        is_cupom: Filtrar pela presença de itens com cupom.
        db: Sessão do banco injetada via Depends.

    Returns:
        Lista de compras com eager loading de mercado, itens e produtos.
    """
    query = (
        db.query(Compra)
        .options(
            selectinload(Compra.mercado),
            selectinload(Compra.itens).selectinload(CompraItem.produto),
        )
    )

    if mercado_id is not None:
        query = query.filter(Compra.mercado_id == mercado_id)

    if data_inicio is not None:
        query = query.filter(Compra.data >= data_inicio)

    if data_fim is not None:
        query = query.filter(Compra.data <= data_fim)

    # SQLite strftime: %w retorna 0=domingo, 1=segunda... 6=sábado.
    # Convertemos para o padrão ISO (0=segunda, 6=domingo).
    if dia_semana is not None:
        sqlite_dow = (dia_semana + 1) % 7  # ISO -> SQLite
        from sqlalchemy import func
        query = query.filter(
            func.cast(func.strftime("%w", Compra.data), type_=None)
            == str(sqlite_dow)
        )

    if is_cupom is not None:
        if is_cupom:
            query = query.filter(
                Compra.itens.any(CompraItem.is_cupom == True)  # noqa: E712
            )
        else:
            query = query.filter(
                ~Compra.itens.any(CompraItem.is_cupom == True)  # noqa: E712
            )

    return query.all()


@router.get(
    "/{compra_id}",
    response_model=CompraResponse,
    summary="Retorna uma compra específica",
)
def obter_compra(compra_id: int, db: Session = Depends(get_db)) -> Compra:
    """Busca uma compra pelo ID com todos os itens e relacionamentos.

    Args:
        compra_id: ID da compra desejada.
        db: Sessão do banco injetada via Depends.

    Returns:
        A compra com mercado, itens e produtos carregados.

    Raises:
        HTTPException: 404 se a compra não for encontrada.
    """
    return _carregar_compra_completa(db, compra_id)


@router.delete(
    "/{compra_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove uma compra",
)
def deletar_compra(
    compra_id: int, db: Session = Depends(get_db)
) -> None:
    """Remove uma compra e todos os seus itens (cascade delete).

    Args:
        compra_id: ID da compra a ser removida.
        db: Sessão do banco injetada via Depends.

    Raises:
        HTTPException: 404 se a compra não for encontrada.
    """
    compra = db.query(Compra).filter(Compra.id == compra_id).first()
    if compra is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compra com id={compra_id} não encontrada.",
        )
    db.delete(compra)
    db.commit()


# ---------------------------------------------------------------------------
# CRUD de Itens individuais
# ---------------------------------------------------------------------------

@router.post(
    "/{compra_id}/itens/",
    response_model=CompraItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adiciona um item a uma compra existente",
)
def adicionar_item(
    compra_id: int,
    item: CompraItemCreate,
    db: Session = Depends(get_db),
) -> CompraItem:
    """Adiciona um item avulso a uma compra já registrada.

    Útil para corrigir ou complementar uma nota fiscal após o registro
    inicial.

    Args:
        compra_id: ID da compra onde o item será adicionado.
        item: Payload validado com os dados do item.
        db: Sessão do banco injetada via Depends.

    Returns:
        O item recém-criado com produto e dados completos.

    Raises:
        HTTPException: 404 se a compra não for encontrada.
    """
    compra = db.query(Compra).filter(Compra.id == compra_id).first()
    if compra is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compra com id={compra_id} não encontrada.",
        )

    db_item = CompraItem(compra_id=compra_id, **item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    # Recarregar com o produto associado para serialização.
    db_item = (
        db.query(CompraItem)
        .options(selectinload(CompraItem.produto))
        .filter(CompraItem.id == db_item.id)
        .first()
    )
    return db_item


@router.delete(
    "/itens/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove um item individual",
)
def deletar_item(
    item_id: int, db: Session = Depends(get_db)
) -> None:
    """Remove um item individual de uma compra.

    Args:
        item_id: ID do item a ser removido.
        db: Sessão do banco injetada via Depends.

    Raises:
        HTTPException: 404 se o item não for encontrado.
    """
    item = db.query(CompraItem).filter(CompraItem.id == item_id).first()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item com id={item_id} não encontrado.",
        )
    db.delete(item)
    db.commit()
