"""
Módulo de configuração do banco de dados.

Responsável por:
- Carregar variáveis de ambiente via python-dotenv.
- Criar o engine do SQLAlchemy a partir de DATABASE_URL.
- Fornecer a fábrica de sessões (SessionLocal).
- Expor a classe Base para herança dos modelos ORM.
- Implementar o gerador get_db() para injeção de dependência no FastAPI.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Carrega as variáveis de ambiente do arquivo .env na raiz do projeto.
load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/precos.db")

# Argumentos específicos de conexão.
# check_same_thread=False é obrigatório para SQLite quando utilizado
# com FastAPI (múltiplas threads/requests concorrentes).
connect_args: dict = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Gerador de sessão do banco de dados para injeção de dependência.

    Utilizado como parâmetro ``Depends(get_db)`` nas rotas do FastAPI.
    Garante que a sessão seja sempre fechada após o processamento da
    requisição, independentemente de sucesso ou exceção.

    Yields:
        Session: Instância ativa da sessão do SQLAlchemy.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
