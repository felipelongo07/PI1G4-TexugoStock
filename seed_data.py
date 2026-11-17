"""
Script para popular o banco de dados do TexugoStock Enterprise com dados corporativos realistas.
Garante cenários para testes e demonstrações:
- Produtos com validade normal
- Produtos próximos do vencimento (alerta amarelo)
- Produtos já vencidos (alerta vermelho)
- Produtos com estoque baixo (alerta de reposição)
- Produtos com estoque zerado
"""
from datetime import date, timedelta
from werkzeug.security import generate_password_hash
from app.database import get_db_connection, init_db

def seed():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    hoje = date.today()

    # Limpa dados anteriores na ordem correta das foreign keys
    cursor.execute("DELETE FROM movimentacoes")
    cursor.execute("DELETE FROM lotes")
    cursor.execute("DELETE FROM produtos")
    cursor.execute("DELETE FROM fornecedores")
    cursor.execute("DELETE FROM usuarios")

    # 1. Garante usuários padrão corporativos
    cursor.execute("""
    INSERT INTO usuarios (nome, email, senha_hash, perfil, cargo) VALUES
    ('Administrador Geral', 'admin@texugostock.com', ?, 'admin', 'Gerente Geral'),
    ('Carlos Silva (Estoque)', 'estoque@texugostock.com', ?, 'estoquista', 'Encarregado de Estoque'),
    ('Ana Paula (Vendas / Caixa)', 'vendas@texugostock.com', ?, 'estoquista', 'Operadora de Caixa')
    """, (
        generate_password_hash('admin123'),
        generate_password_hash('estoque123'),
        generate_password_hash('vendas123')
    ))

    # 2. Fornecedores Homologados
    cursor.execute("""
    INSERT INTO fornecedores (razao_social, nome_fantasia, cnpj, telefone, email, contato_responsavel, cidade, uf) VALUES
    ('Ambev Brasil Bebidas S/A', 'Cervejaria Ambev', '02.808.708/0001-07', '(11) 4004-1000', 'pedidos@ambev.com.br', 'Marcos Vendas', 'São Paulo', 'SP'),
    ('Laticínios Alvorada Indústria e Comércio Ltda.', 'Laticínios Alvorada', '18.234.567/0001-89', '(19) 3876-1122', 'comercial@alvorada.ind.br', 'Renata Vendedora', 'Campinas', 'SP'),
    ('Danone Alimentos do Brasil Ltda.', 'Danone Distribuidora', '43.210.987/0001-12', '(11) 3740-2000', 'atendimento@danone.com.br', 'Lucas Representante', 'São Paulo', 'SP'),
    ('Cerealista São Jorge Grãos e Alimentos Ltda.', 'Cerealista São Jorge', '55.678.901/0001-34', '(14) 3402-9900', 'vendas@saojorge.com.br', 'Jorge Diretor', 'Marília', 'SP'),
    ('Adega & Vinhedos Vale dos Vinhedos S/A', 'Adega Serra Gaúcha', '90.123.456/0001-78', '(54) 3455-8800', 'contato@serragaucha.com.br', 'Eduardo Sommelier', 'Bento Gonçalves', 'RS'),
    ('Distribuidora São Paulo Frios e Laticínios Ltda.', 'Distribuidora São Paulo', '33.444.555/0001-66', '(11) 2233-4455', 'pedidos@friossp.com.br', 'Claudio Vendas', 'São Paulo', 'SP'),
    ('Panificadora & Moagem Central Ltda.', 'Panificadora Central', '77.888.999/0001-22', '(11) 3100-7788', 'panificacao@central.com.br', 'Fernando Padeiro', 'São Paulo', 'SP')
    """)

    # 2. Produtos do Catálogo (Foco no perfil de mercadinhos, adegas e mercearias)
    produtos_exemplo = [
        # (codigo, nome, categoria, unidade, preco_custo, preco_venda, estoque_minimo, descricao)
        ('7891000100101', 'Leite Integral UHT 1L', 'Laticínios', 'UN', 3.80, 5.49, 20, 'Leite integral longa vida 1 Litro'),
        ('7891000100102', 'Iogurte Natural 170g', 'Laticínios', 'UN', 2.10, 3.89, 15, 'Iogurte integral sem adição de açúcares'),
        ('7891000100103', 'Queijo Mussarela Fatiado 200g', 'Frios e Queijos', 'PCT', 7.50, 11.90, 10, 'Queijo fatiado embalagem a vácuo'),
        ('7891000100104', 'Refrigerante Cola 2L', 'Bebidas', 'UN', 5.20, 8.99, 24, 'Refrigerante tradicional sabor cola 2 Litros'),
        ('7891000100105', 'Cerveja Puro Malte Lata 350ml', 'Bebidas / Adega', 'UN', 2.90, 4.79, 30, 'Cerveja puro malte pilsen lata 350ml'),
        ('7891000100106', 'Vinho Tinto Seco Reservado 750ml', 'Bebidas / Adega', 'GFA', 18.00, 34.90, 8, 'Vinho fino de mesa tinto seco'),
        ('7891000100107', 'Arroz Branco Tipo 1 5kg', 'Mercearia', 'PCT', 19.50, 27.90, 12, 'Arroz agulhinha longo fino tipo 1'),
        ('7891000100108', 'Feijão Carioca 1kg', 'Mercearia', 'PCT', 5.80, 8.50, 15, 'Feijão carioca selecionado 1kg'),
        ('7891000100109', 'Óleo de Soja Refinado 900ml', 'Mercearia', 'UN', 4.30, 6.70, 18, 'Óleo vegetal de soja refinado pet'),
        ('7891000100110', 'Pão de Forma Tradicional 500g', 'Padaria', 'PCT', 4.50, 7.99, 8, 'Pão fatiado embalagem plástica'),
        ('7891000100111', 'Café Torrado e Moído Tradicional 500g', 'Mercearia', 'PCT', 11.20, 17.50, 10, 'Café a vácuo ponto tradicional'),
        ('7891000100112', 'Biscoito Recheado Chocolate 140g', 'Mercearia', 'PCT', 1.80, 3.20, 20, 'Biscoito recheio duplo sabor chocolate')
    ]

    prod_ids = {}
    for p in produtos_exemplo:
        cursor.execute("""
        INSERT INTO produtos (codigo_barras, nome, categoria, unidade_medida, preco_custo, preco_venda, estoque_minimo, descricao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, p)
        prod_ids[p[1]] = cursor.lastrowid

    # 3. Inserção de Lotes com Cenários Didáticos para Apresentação
    # Cenário A: Produto com lote vencido e lote normal (Leite Integral) -> Testar FEFO e Alerta Vermelho
    cursor.execute("""
    INSERT INTO lotes (produto_id, numero_lote, quantidade_inicial, quantidade_atual, data_validade, fornecedor, observacoes)
    VALUES (?, 'LT-LEITE-VENC', 10, 8, ?, 'Laticínios Alvorada', 'Lote antigo esquecido no fundo da câmara fria')
    """, (prod_ids['Leite Integral UHT 1L'], (hoje - timedelta(days=5)).isoformat()))
    lote_leite_venc = cursor.lastrowid

    cursor.execute("""
    INSERT INTO lotes (produto_id, numero_lote, quantidade_inicial, quantidade_atual, data_validade, fornecedor, observacoes)
    VALUES (?, 'LT-LEITE-NOVO', 50, 45, ?, 'Laticínios Alvorada', 'Recebido ontem')
    """, (prod_ids['Leite Integral UHT 1L'], (hoje + timedelta(days=90)).isoformat()))
    lote_leite_novo = cursor.lastrowid

    # Cenário B: Produto PRÓXIMO DO VENCIMENTO (Iogurte Natural - vence em 4 dias!) -> Alerta Amarelo
    cursor.execute("""
    INSERT INTO lotes (produto_id, numero_lote, quantidade_inicial, quantidade_atual, data_validade, fornecedor, observacoes)
    VALUES (?, 'LT-IOG-04D', 25, 18, ?, 'Danone Distribuidora', 'Atenção: colocar em promoção relâmpago!')
    """, (prod_ids['Iogurte Natural 170g'], (hoje + timedelta(days=4)).isoformat()))
    lote_iog = cursor.lastrowid

    # Cenário C: Pão de Forma com vencimento em 7 dias (próximo do vencimento)
    cursor.execute("""
    INSERT INTO lotes (produto_id, numero_lote, quantidade_inicial, quantidade_atual, data_validade, fornecedor, observacoes)
    VALUES (?, 'LT-PAO-07D', 12, 6, ?, 'Panificadora Central', 'Estoque baixo e a vencer em breve')
    """, (prod_ids['Pão de Forma Tradicional 500g'], (hoje + timedelta(days=7)).isoformat()))
    lote_pao = cursor.lastrowid

    # Cenário D: Queijo Mussarela com estoque baixo (quantidade atual = 4, mínimo = 10) -> Alerta de Reposição
    cursor.execute("""
    INSERT INTO lotes (produto_id, numero_lote, quantidade_inicial, quantidade_atual, data_validade, fornecedor, observacoes)
    VALUES (?, 'LT-QUEIJO-01', 15, 4, ?, 'Distribuidora São Paulo', 'Lote em final de estoque')
    """, (prod_ids['Queijo Mussarela Fatiado 200g'], (hoje + timedelta(days=22)).isoformat()))
    lote_queijo = cursor.lastrowid

    # Cenário E: Refrigerante Cola com estoque excelente e validade longa
    cursor.execute("""
    INSERT INTO lotes (produto_id, numero_lote, quantidade_inicial, quantidade_atual, data_validade, fornecedor, observacoes)
    VALUES (?, 'LT-COLA-101', 60, 48, ?, 'Distribuidora de Bebidas Brasil', 'Lote principal')
    """, (prod_ids['Refrigerante Cola 2L'], (hoje + timedelta(days=180)).isoformat()))
    lote_cola = cursor.lastrowid

    # Cenário F: Cerveja Puro Malte com 2 lotes (um vence em 30 dias e outro em 120 dias) -> Perfeito para demonstrar FEFO
    cursor.execute("""
    INSERT INTO lotes (produto_id, numero_lote, quantidade_inicial, quantidade_atual, data_validade, fornecedor, observacoes)
    VALUES (?, 'LT-CERV-FEFO-1', 40, 15, ?, 'Cervejaria Ambev', 'Lote mais antigo - deve sair primeiro')
    """, (prod_ids['Cerveja Puro Malte Lata 350ml'], (hoje + timedelta(days=25)).isoformat()))
    lote_cerv1 = cursor.lastrowid

    cursor.execute("""
    INSERT INTO lotes (produto_id, numero_lote, quantidade_inicial, quantidade_atual, data_validade, fornecedor, observacoes)
    VALUES (?, 'LT-CERV-FEFO-2', 60, 55, ?, 'Cervejaria Ambev', 'Lote mais recente')
    """, (prod_ids['Cerveja Puro Malte Lata 350ml'], (hoje + timedelta(days=150)).isoformat()))
    lote_cerv2 = cursor.lastrowid

    # Cenário G: Vinho Tinto - estoque normal
    cursor.execute("""
    INSERT INTO lotes (produto_id, numero_lote, quantidade_inicial, quantidade_atual, data_validade, fornecedor, observacoes)
    VALUES (?, 'LT-VINHO-2026', 20, 14, ?, 'Adega Serra Gaúcha', 'Vinho de guarda')
    """, (prod_ids['Vinho Tinto Seco Reservado 750ml'], (hoje + timedelta(days=720)).isoformat()))

    # Cenário H: Arroz e Feijão com bons estoques
    cursor.execute("""
    INSERT INTO lotes (produto_id, numero_lote, quantidade_inicial, quantidade_atual, data_validade, fornecedor, observacoes)
    VALUES (?, 'LT-ARROZ-01', 30, 26, ?, 'Cerealista São Jorge', 'Pallet A')
    """, (prod_ids['Arroz Branco Tipo 1 5kg'], (hoje + timedelta(days=240)).isoformat()))

    cursor.execute("""
    INSERT INTO lotes (produto_id, numero_lote, quantidade_inicial, quantidade_atual, data_validade, fornecedor, observacoes)
    VALUES (?, 'LT-FEIJAO-01', 25, 20, ?, 'Cerealista São Jorge', 'Pallet B')
    """, (prod_ids['Feijão Carioca 1kg'], (hoje + timedelta(days=180)).isoformat()))

    # Cenário I: Óleo de Soja com estoque zerado (sem lotes ativos) -> Alerta de Estoque Esgotado / Reposição Urgente

    # 4. Histórico de Movimentações Recentes para Enriquecer o Dashboard
    u_estoque = cursor.execute("SELECT id FROM usuarios WHERE email = 'estoque@texugostock.com'").fetchone()['id']
    u_vendas = cursor.execute("SELECT id FROM usuarios WHERE email = 'vendas@texugostock.com'").fetchone()['id']

    cursor.execute("""
    INSERT INTO movimentacoes (produto_id, lote_id, tipo, quantidade, usuario_id, motivo, data_hora) VALUES
    (?, ?, 'ENTRADA', 50, ?, 'Recebimento de Mercadoria - NF 44102', datetime('now', '-2 days')),
    (?, ?, 'SAIDA_VENDA', 5, ?, 'Venda Balcão Caixa 01', datetime('now', '-1 days')),
    (?, ?, 'ENTRADA', 25, ?, 'Recebimento Iogurtes - NF 88310', datetime('now', '-1 days')),
    (?, ?, 'SAIDA_VENDA', 7, ?, 'Venda Balcão Caixa 02', datetime('now', '-4 hours'))
    """, (
        prod_ids['Leite Integral UHT 1L'], lote_leite_novo, u_estoque,
        prod_ids['Leite Integral UHT 1L'], lote_leite_novo, u_vendas,
        prod_ids['Iogurte Natural 170g'], lote_iog, u_estoque,
        prod_ids['Iogurte Natural 170g'], lote_iog, u_vendas
    ))

    conn.commit()
    conn.close()
    print("Banco de dados TexugoStock populado com sucesso com dados da apresentação!")

if __name__ == '__main__':
    seed()

