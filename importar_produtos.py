import json
import os
import sys

from sqlalchemy import select
from app.database import SessionLocal
from app.models import Produto

def importar_produtos_de_json(caminho_arquivo: str):
    if not os.path.exists(caminho_arquivo):
        print(f"Erro: Arquivo {caminho_arquivo} não encontrado.")
        sys.exit(1)

    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        try:
            dados = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Erro ao ler o JSON: {e}")
            sys.exit(1)

    with SessionLocal() as db:
        novos_produtos = 0
        produtos_ignorados = 0
        
        # Buscar todos os produtos existentes para evitar duplicatas
        produtos_existentes = db.execute(select(Produto)).scalars().all()
        # Set para busca rápida: (tipo, subtipo, marca, conteudo, unidade)
        set_existentes = set(
            (
                p.tipo.lower(),
                p.subtipo.lower() if p.subtipo else "",
                p.marca.lower(),
                float(p.conteudo_embalagem),
                p.unidade_medida.lower()
            )
            for p in produtos_existentes
        )

        for item in dados:
            # Normalização das chaves do JSON para o padrão do Banco de Dados
            tipo = item.get("tipo")
            subtipo = item.get("subtipo")
            marca = item.get("marca")
            categoria = item.get("categoria")
            conteudo = float(item.get("conteudo_da_embalagem"))
            
            # Normalizar a unidade (ex: 'und' para 'un')
            unidade = item.get("unidade", "").lower()
            if unidade == "und":
                unidade = "un"

            # Chave de comparação para evitar duplicidade
            chave = (
                tipo.lower(),
                subtipo.lower() if subtipo else "",
                marca.lower(),
                conteudo,
                unidade
            )

            if chave in set_existentes:
                produtos_ignorados += 1
                continue

            # Criar novo produto
            novo_produto = Produto(
                tipo=tipo,
                subtipo=subtipo,
                marca=marca,
                categoria=categoria,
                conteudo_embalagem=conteudo,
                unidade_medida=unidade
            )
            db.add(novo_produto)
            set_existentes.add(chave)  # Adiciona ao set para caso o próprio JSON tenha itens duplicados (como a melancia)
            novos_produtos += 1

        db.commit()
        print("--- Relatório de Importação ---")
        print(f"Total lido no JSON: {len(dados)}")
        print(f"Produtos importados: {novos_produtos}")
        print(f"Duplicatas ignoradas: {produtos_ignorados}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Importa produtos de um arquivo JSON para o banco de dados.")
    parser.add_argument("arquivo", help="Caminho para o arquivo JSON")
    args = parser.parse_args()
    
    print(f"Iniciando importação do arquivo: {args.arquivo}")
    importar_produtos_de_json(args.arquivo)
