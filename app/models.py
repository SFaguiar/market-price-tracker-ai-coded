"""
Modelos ORM do SQLAlchemy 2.0+.

Define o mapeamento objeto-relacional para as tabelas do banco de dados
utilizando a sintaxe moderna com ``Mapped`` e ``mapped_column``.

Tabelas:
    - mercados: Estabelecimentos comerciais onde as compras são realizadas.
    - produtos: Itens individuais rastreados pelo sistema.
    - compras: Registros de visitas a um mercado em uma data específica.
    - compras_itens: Itens adquiridos em cada compra, com metadados de preço
      e flags de controle de viés analítico.
"""

import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Date, Float, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Rede(Base):
    """Representa um conglomerado ou rede de supermercados (ex: Carrefour, Assaí)."""

    __tablename__ = "redes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    mercados: Mapped[List["Mercado"]] = relationship(
        back_populates="rede",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Rede(id={self.id}, nome='{self.nome}')>"


class Mercado(Base):
    """Representa um estabelecimento comercial.

    Attributes:
        id: Identificador único auto-incrementado.
        nome: Nome do estabelecimento (ex: 'Atacadão Mineirão').
        tipo: Classificação do tipo de comércio. Valores esperados:
              'Atacado', 'Supermercado', 'Mercado de Bairro', 'Feira', 'Outros'.
        endereco: Endereço textual do estabelecimento (ex: 'Av. Brasil, 1500').
        cidade: Cidade onde o estabelecimento está localizado.
        estado: Sigla UF do estado (ex: 'MG', 'SP').
        latitude: Coordenada geográfica de latitude (opcional).
        longitude: Coordenada geográfica de longitude (opcional).
        compras: Lista de compras realizadas neste mercado.
    """

    __tablename__ = "mercados"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rede_id: Mapped[Optional[int]] = mapped_column(ForeignKey("redes.id"), nullable=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    endereco: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    cidade: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    estado: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6), nullable=True)

    rede: Mapped[Optional["Rede"]] = relationship(back_populates="mercados")
    compras: Mapped[List["Compra"]] = relationship(
        back_populates="mercado",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Mercado(id={self.id}, nome='{self.nome}', tipo='{self.tipo}', cidade='{self.cidade}')>"


class Produto(Base):
    """Representa um produto rastreado pelo sistema.

    A estrutura tipo/subtipo permite agrupamento inteligente para
    comparações e substituições no Carrinho de Compras:
      - tipo: categoria genérica do produto (ex: 'Arroz', 'Feijão', 'Café').
      - subtipo: variação específica (ex: 'Integral', 'Carioca', 'Extra Forte').

    Os campos conteudo_embalagem e unidade_medida descrevem a quantidade
    que vem em cada unidade vendida (ex: 12 un de ovos, 1 kg de arroz,
    500 ml de leite), habilitando o cálculo de preço por unidade padrão.

    Attributes:
        id: Identificador único auto-incrementado.
        tipo: Tipo genérico do produto (ex: 'Arroz', 'Feijão').
        subtipo: Variação do tipo (ex: 'Integral', 'Carioca'). Opcional.
        marca: Marca do fabricante (ex: 'Camil', 'Tio João').
        categoria: Classificação de seção (ex: 'Mercearia', 'Hortifrúti').
        conteudo_embalagem: Quantidade contida na embalagem (ex: 1.000 para 1kg).
        unidade_medida: Unidade de medida do conteúdo ('kg', 'g', 'l', 'ml', 'un').
        compras_itens: Lista de registros de compra onde este produto aparece.
    """

    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tipo: Mapped[str] = mapped_column(String(100), nullable=False)
    subtipo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    marca: Mapped[str] = mapped_column(String(100), nullable=False)
    categoria: Mapped[str] = mapped_column(String(100), nullable=False)
    conteudo_embalagem: Mapped[Decimal] = mapped_column(
        Numeric(10, 3), nullable=False
    )
    unidade_medida: Mapped[str] = mapped_column(String(10), nullable=False)

    compras_itens: Mapped[List["CompraItem"]] = relationship(
        back_populates="produto",
    )

    def __repr__(self) -> str:
        label = f"{self.tipo}"
        if self.subtipo:
            label += f" {self.subtipo}"
        return f"<Produto(id={self.id}, '{label}', marca='{self.marca}', {self.conteudo_embalagem}{self.unidade_medida})>"


class Compra(Base):
    """Representa uma visita de compras a um mercado em uma data específica.

    Attributes:
        id: Identificador único auto-incrementado.
        mercado_id: Chave estrangeira referenciando o mercado visitado.
        data: Data da compra em formato ISO (YYYY-MM-DD).
        nfe: Número da Nota Fiscal Eletrônica (opcional).
        observacoes: Campo de texto livre para anotações sobre a compra.
        mercado: Relacionamento bidirecional com o objeto Mercado.
        itens: Lista de itens adquiridos nesta compra (cascade delete).
    """

    __tablename__ = "compras"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    mercado_id: Mapped[int] = mapped_column(
        ForeignKey("mercados.id"), nullable=False
    )
    data: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    nfe: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    observacoes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    mercado: Mapped["Mercado"] = relationship(back_populates="compras")
    itens: Mapped[List["CompraItem"]] = relationship(
        back_populates="compra",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Compra(id={self.id}, mercado_id={self.mercado_id}, data='{self.data}', nfe='{self.nfe}')>"


class CompraItem(Base):
    """Representa um item individual dentro de uma compra.

    Contém o preço pago, quantidade de embalagens compradas e flags
    de controle que permitem isolar ruídos analíticos (promoções, cupons,
    fidelidade, produtos próximos da validade).

    O cálculo de preço por unidade padrão é derivado do produto vinculado,
    que contém conteudo_embalagem e unidade_medida.

    Attributes:
        id: Identificador único auto-incrementado.
        compra_id: FK para a compra pai (cascade delete no banco).
        produto_id: FK para o produto adquirido.
        preco_pago: Preço unitário final impresso na nota fiscal.
        quantidade: Quantidade de embalagens adquiridas (suporta frações).
        is_promocao: Flag indicando preço promocional.
        is_cupom: Flag indicando uso de cupom de desconto.
        is_fidelidade: Flag indicando exigência de cadastro/CPF.
        is_validade_proxima: Flag indicando produto da seção "vencinho".
        fonte_dado: Origem do dado ('cupom_fiscal' ou 'pesquisa_gondola').
        compra: Relacionamento bidirecional com o objeto Compra.
        produto: Relacionamento bidirecional com o objeto Produto.
    """

    __tablename__ = "compras_itens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    compra_id: Mapped[int] = mapped_column(
        ForeignKey("compras.id", ondelete="CASCADE"), nullable=False
    )
    produto_id: Mapped[int] = mapped_column(
        ForeignKey("produtos.id"), nullable=False
    )
    preco_pago: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False
    )
    quantidade: Mapped[Decimal] = mapped_column(
        Numeric(10, 3), nullable=False
    )
    is_promocao: Mapped[bool] = mapped_column(default=False)
    is_cupom: Mapped[bool] = mapped_column(default=False)
    is_fidelidade: Mapped[bool] = mapped_column(default=False)
    is_validade_proxima: Mapped[bool] = mapped_column(default=False)
    fonte_dado: Mapped[str] = mapped_column(String(30), nullable=False)

    compra: Mapped["Compra"] = relationship(back_populates="itens")
    produto: Mapped["Produto"] = relationship(back_populates="compras_itens")

    def __repr__(self) -> str:
        return (
            f"<CompraItem(id={self.id}, produto_id={self.produto_id}, "
            f"preco_pago={self.preco_pago})>"
        )
