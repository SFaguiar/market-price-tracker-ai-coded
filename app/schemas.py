"""
Esquemas Pydantic v2 para validação de entrada e serialização de saída.

Para cada entidade do sistema, existem três variações de classe:
    - ``Base``: Campos comuns compartilhados entre criação e leitura.
    - ``Create``: Payload de entrada para POST (sem campo ``id``).
    - ``Response``: Serialização de saída para GET (com ``id`` e
      ``from_attributes=True`` para conversão automática de modelos ORM).

Destaque:
    O ``CompraItemResponse`` inclui o campo calculado
    ``preco_por_unidade_padrao``, que normaliza o preço para 1kg ou 1L,
    permitindo a detecção de shrinkflation e a comparação justa entre
    embalagens de tamanhos diferentes.
"""

import datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field


# ---------------------------------------------------------------------------
# Rede
# ---------------------------------------------------------------------------

class RedeBase(BaseModel):
    """Campos compartilhados para a entidade Rede."""
    model_config = ConfigDict(str_strip_whitespace=True)
    nome: str

class RedeCreate(RedeBase):
    """Schema de criação de Rede (POST). Não inclui ``id``."""
    pass

class RedeResponse(RedeBase):
    """Schema de resposta de Rede (GET). Inclui ``id``."""
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------------------------------------------------------------------------
# Mercado
# ---------------------------------------------------------------------------

class MercadoBase(BaseModel):
    """Campos compartilhados para a entidade Mercado."""
    model_config = ConfigDict(str_strip_whitespace=True)

    nome: str
    rede_id: Optional[int] = None
    tipo: str
    endereco: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    latitude: Optional[Decimal] = Field(default=None, max_digits=9, decimal_places=6)
    longitude: Optional[Decimal] = Field(default=None, max_digits=9, decimal_places=6)


class MercadoCreate(MercadoBase):
    """Schema de criação de Mercado (POST). Não inclui ``id``."""

    pass


class MercadoResponse(MercadoBase):
    """Schema de resposta de Mercado (GET). Inclui ``id``."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    rede: Optional[RedeResponse] = None


# ---------------------------------------------------------------------------
# Produto
# ---------------------------------------------------------------------------

class ProdutoBase(BaseModel):
    """Campos compartilhados para a entidade Produto.

    A estrutura tipo/subtipo permite agrupamento inteligente:
      - tipo: categoria genérica (ex: 'Arroz', 'Feijão', 'Café').
      - subtipo: variação específica (ex: 'Integral', 'Carioca').

    conteudo_embalagem e unidade_medida descrevem o conteúdo da
    embalagem vendida (ex: 12 un, 1 kg, 500 ml).
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    tipo: str
    subtipo: Optional[str] = None
    marca: str
    categoria: Literal[
        "Açougue", "Bazar", "Bebidas", "Congelados", "Frios e Laticínios", 
        "Higiene Pessoal", "Hortifrúti", "Limpeza", "Mercearia", "Padaria", 
        "Pet Shop", "Utilidades Domésticas"
    ]
    conteudo_embalagem: Decimal
    unidade_medida: Literal["kg", "g", "l", "ml", "un", "m", "cm"]


class ProdutoCreate(ProdutoBase):
    """Schema de criação de Produto (POST). Não inclui ``id``."""

    pass


class ProdutoResponse(ProdutoBase):
    """Schema de resposta de Produto (GET). Inclui ``id``."""

    model_config = ConfigDict(from_attributes=True)

    id: int


# ---------------------------------------------------------------------------
# CompraItem
# ---------------------------------------------------------------------------

# Fatores de conversão para normalizar unidades para a base padrão (kg ou L).
_FATORES_CONVERSAO: dict[str, Decimal] = {
    "kg": Decimal("1"),
    "g": Decimal("0.001"),
    "l": Decimal("1"),
    "ml": Decimal("0.001"),
    "un": Decimal("1"),  # Unidade discreta — mantém o valor original.
}


class CompraItemBase(BaseModel):
    """Campos compartilhados para a entidade CompraItem.

    Attributes:
        produto_id: FK para o produto adquirido.
        preco_pago: Preço final unitário impresso na nota.
        quantidade: Quantidade de embalagens adquiridas (suporta frações).
        is_promocao: Preço promocional.
        is_cupom: Uso de cupom de desconto.
        is_fidelidade: Exigência de cadastro/CPF para obter o preço.
        is_validade_proxima: Produto da seção "vencinho".
        fonte_dado: Origem do dado coletado.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    produto_id: int
    preco_pago: Decimal
    quantidade: Decimal
    is_promocao: bool = False
    is_cupom: bool = False
    is_fidelidade: bool = False
    is_validade_proxima: bool = False
    fonte_dado: Literal["cupom_fiscal", "pesquisa_gondola"]


class CompraItemCreate(CompraItemBase):
    """Schema de criação de CompraItem (POST). Não inclui ``id``."""

    pass


class CompraItemCreateNested(CompraItemBase):
    """Schema de criação de CompraItem aninhado dentro de uma Compra.

    Não requer ``compra_id`` pois este é inferido do contexto da
    compra pai.
    """

    pass


class CompraItemResponse(CompraItemBase):
    """Schema de resposta de CompraItem (GET).

    Inclui ``id``, dados do produto associado e o campo calculado
    ``preco_por_unidade_padrao`` para análise anti-shrinkflation.

    O cálculo agora utiliza conteudo_embalagem e unidade_medida do
    Produto vinculado, não mais do próprio CompraItem.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    compra_id: int
    produto: ProdutoResponse

    @computed_field  # type: ignore[prop-decorator]
    @property
    def preco_por_unidade_padrao(self) -> Decimal:
        """Calcula o preço normalizado por 1kg ou 1L.

        A normalização permite comparação justa entre embalagens de
        tamanhos diferentes, detectando shrinkflation e variações
        ocultas de preço.

        O cálculo usa conteudo_embalagem e unidade_medida do Produto:
            preço_normalizado = preco_pago / (conteudo_embalagem * fator_conversao)

        Para unidades discretas ('un'), retorna o preço pago por unidade
        individual (preco_pago / conteudo_embalagem).

        Returns:
            Preço por unidade padrão (1kg, 1L ou 1un), arredondado
            para 2 casas decimais.
        """
        fator = _FATORES_CONVERSAO.get(self.produto.unidade_medida, Decimal("1"))
        conteudo_padrao = self.produto.conteudo_embalagem * fator

        if conteudo_padrao == 0:
            return Decimal("0.00")

        preco_normalizado = self.preco_pago / conteudo_padrao
        return preco_normalizado.quantize(Decimal("0.01"))


# ---------------------------------------------------------------------------
# Compra
# ---------------------------------------------------------------------------

class CompraBase(BaseModel):
    """Campos compartilhados para a entidade Compra."""
    model_config = ConfigDict(str_strip_whitespace=True)

    mercado_id: int
    data: datetime.date
    nfe: Optional[str] = None
    observacoes: Optional[str] = None


class CompraCreate(CompraBase):
    """Schema de criação de Compra (POST).

    Permite criar uma compra com seus itens em uma única requisição,
    refletindo a operação natural de registrar uma nota fiscal completa.
    """

    itens: List[CompraItemCreateNested] = []


class CompraResponse(CompraBase):
    """Schema de resposta de Compra (GET).

    Inclui ``id``, dados do mercado associado e a lista completa de
    itens com seus preços normalizados.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    mercado: MercadoResponse
    itens: List[CompraItemResponse] = []
