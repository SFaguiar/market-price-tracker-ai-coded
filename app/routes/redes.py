from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import Rede
from app.schemas import RedeCreate, RedeResponse

router = APIRouter(prefix="/redes", tags=["Redes"])


@router.post("/", response_model=RedeResponse, status_code=status.HTTP_201_CREATED)
def criar_rede(rede: RedeCreate, db: Session = Depends(get_db)):
    """
    Cria uma nova rede de supermercados.
    Retorna erro 400 se já existir uma rede com o mesmo nome.
    """
    nova_rede = Rede(nome=rede.nome)
    db.add(nova_rede)
    
    try:
        db.commit()
        db.refresh(nova_rede)
        return nova_rede
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="Já existe uma rede cadastrada com esse nome."
        )


@router.get("/", response_model=List[RedeResponse])
def listar_redes(db: Session = Depends(get_db)):
    """
    Lista todas as redes cadastradas no sistema.
    """
    redes = db.execute(select(Rede).order_by(Rede.nome)).scalars().all()
    return redes
