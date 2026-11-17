from datetime import date, datetime, timedelta
from app.database import get_db_connection

def obter_configuracao(chave, padrao=None):
    """Obtém um valor de configuração pelo nome da chave."""
    conn = get_db_connection()
    row = conn.execute("SELECT valor FROM configuracoes WHERE chave = ?", (chave,)).fetchone()
    conn.close()
    return row['valor'] if row else padrao

def atualizar_configuracao(chave, valor):
    """Atualiza ou insere uma configuração no sistema."""
    conn = get_db_connection()
    conn.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)", (chave, str(valor)))
    conn.commit()
    conn.close()

def calcular_status_validade(data_validade_str, dias_alerta=None):
    """
    Retorna a classificação do lote:
    - 'VENCIDO': data < hoje
    - 'PROXIMO': hoje <= data <= hoje + dias_alerta
    - 'OK': data > hoje + dias_alerta
    E também a contagem de dias restantes (negativo se vencido).
    """
    if dias_alerta is None:
        dias_alerta = int(obter_configuracao('dias_alerta_validade', 15))

    hoje = date.today()
    if isinstance(data_validade_str, str):
        data_validade = datetime.strptime(data_validade_str[:10], '%Y-%m-%d').date()
    else:
        data_validade = data_validade_str

    dias_restantes = (data_validade - hoje).days

    if dias_restantes < 0:
        return 'VENCIDO', dias_restantes
    elif dias_restantes <= dias_alerta:
        return 'PROXIMO', dias_restantes
    else:
        return 'OK', dias_restantes

def listar_produtos(busca=None, categoria=None, status_filtro=None):
    """
    Retorna todos os produtos ativos com o cálculo consolidado
    de estoque atual, estoque mínimo, status de reposição e status crítico de validade.
    """
    conn = get_db_connection()
    dias_alerta = int(obter_configuracao('dias_alerta_validade', 15))

    query = """
    SELECT 
        p.*,
        COALESCE(SUM(l.quantidade_atual), 0) AS estoque_atual,
        COUNT(l.id) AS total_lotes_ativos
    FROM produtos p
    LEFT JOIN lotes l ON p.id = l.produto_id AND l.quantidade_atual > 0
    WHERE p.ativo = 1
    """
    params = []

    if busca:
        query += " AND (p.nome LIKE ? OR p.codigo_barras LIKE ? OR p.categoria LIKE ?)"
        termo = f"%{busca}%"
        params.extend([termo, termo, termo])

    if categoria:
        query += " AND p.categoria = ?"
        params.append(categoria)

    query += " GROUP BY p.id ORDER BY p.nome ASC"

    rows = conn.execute(query, params).fetchall()
    produtos = []

    for r in rows:
        prod = dict(r)
        
        # Determina status do estoque
        if prod['estoque_atual'] <= 0:
            prod['status_estoque'] = 'ZERADO'
            prod['badge_estoque'] = 'danger'
        elif prod['estoque_atual'] <= prod['estoque_minimo']:
            prod['status_estoque'] = 'BAIXO'
            prod['badge_estoque'] = 'warning'
        else:
            prod['status_estoque'] = 'NORMAL'
            prod['badge_estoque'] = 'success'

        # Verifica se o produto tem lotes vencidos ou a vencer
        lotes_prod = conn.execute("""
            SELECT data_validade, quantidade_atual 
            FROM lotes 
            WHERE produto_id = ? AND quantidade_atual > 0 
            ORDER BY data_validade ASC
        """, (prod['id'],)).fetchall()

        tem_vencido = False
        tem_proximo = False
        menor_dias = None

        for lt in lotes_prod:
            status_val, dias = calcular_status_validade(lt['data_validade'], dias_alerta)
            if menor_dias is None or dias < menor_dias:
                menor_dias = dias
            if status_val == 'VENCIDO':
                tem_vencido = True
            elif status_val == 'PROXIMO':
                tem_proximo = True

        if tem_vencido:
            prod['status_validade_geral'] = 'VENCIDO'
            prod['dias_validade_proxima'] = menor_dias
        elif tem_proximo:
            prod['status_validade_geral'] = 'PROXIMO'
            prod['dias_validade_proxima'] = menor_dias
        else:
            prod['status_validade_geral'] = 'OK'
            prod['dias_validade_proxima'] = menor_dias

        # Filtro opcional por status
        if status_filtro:
            if status_filtro == 'BAIXO' and prod['status_estoque'] not in ('BAIXO', 'ZERADO'):
                continue
            if status_filtro == 'VENCIDO' and not tem_vencido:
                continue
            if status_filtro == 'PROXIMO' and not tem_proximo:
                continue

        produtos.append(prod)

    conn.close()
    return produtos

def obter_produto_por_id(produto_id):
    """Busca os detalhes de um produto e consolida seu estoque."""
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM produtos WHERE id = ? AND ativo = 1", (produto_id,)).fetchone()
    if not row:
        conn.close()
        return None
    
    prod = dict(row)
    saldo = conn.execute("SELECT COALESCE(SUM(quantidade_atual), 0) AS total FROM lotes WHERE produto_id = ? AND quantidade_atual > 0", (produto_id,)).fetchone()
    prod['estoque_atual'] = saldo['total']
    conn.close()
    return prod

def cadastrar_produto(dados):
    """Cadastra um novo produto no catálogo (RF01)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO produtos (codigo_barras, nome, categoria, unidade_medida, preco_custo, preco_venda, estoque_minimo, descricao)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dados.get('codigo_barras') or None,
        dados['nome'].strip(),
        dados['categoria'].strip(),
        dados.get('unidade_medida', 'UN'),
        float(dados.get('preco_custo', 0) or 0),
        float(dados.get('preco_venda', 0) or 0),
        int(dados.get('estoque_minimo', 5) or 5),
        dados.get('descricao', '').strip()
    ))
    novo_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return novo_id

def editar_produto(produto_id, dados):
    """Atualiza as informações de um produto existente."""
    conn = get_db_connection()
    conn.execute("""
    UPDATE produtos
    SET codigo_barras = ?, nome = ?, categoria = ?, unidade_medida = ?,
        preco_custo = ?, preco_venda = ?, estoque_minimo = ?, descricao = ?
    WHERE id = ?
    """, (
        dados.get('codigo_barras') or None,
        dados['nome'].strip(),
        dados['categoria'].strip(),
        dados.get('unidade_medida', 'UN'),
        float(dados.get('preco_custo', 0) or 0),
        float(dados.get('preco_venda', 0) or 0),
        int(dados.get('estoque_minimo', 5) or 5),
        dados.get('descricao', '').strip(),
        produto_id
    ))
    conn.commit()
    conn.close()

def excluir_produto(produto_id):
    """Desativa um produto do catálogo (soft delete)."""
    conn = get_db_connection()
    conn.execute("UPDATE produtos SET ativo = 0 WHERE id = ?", (produto_id,))
    conn.commit()
    conn.close()

def registrar_entrada_lote(produto_id, numero_lote, quantidade, data_validade, fornecedor='', observacoes='', usuario_id=None):
    """
    Registra o recebimento de mercadorias no estoque com lote e validade (RF02, RF03).
    Gera automaticamente a movimentação do tipo 'ENTRADA'.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Validação do produto
    prod = cursor.execute("SELECT id, nome FROM produtos WHERE id = ? AND ativo = 1", (produto_id,)).fetchone()
    if not prod:
        conn.close()
        raise ValueError("Produto selecionado não foi encontrado ou está inativo.")

    qtd = int(quantidade)
    if qtd <= 0:
        conn.close()
        raise ValueError("A quantidade de entrada deve ser maior que zero.")

    # Insere o lote
    cursor.execute("""
    INSERT INTO lotes (produto_id, numero_lote, quantidade_inicial, quantidade_atual, data_validade, fornecedor, observacoes)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (produto_id, numero_lote.strip(), qtd, qtd, data_validade, fornecedor.strip(), observacoes.strip()))
    lote_id = cursor.lastrowid

    # Registra movimentação de entrada
    cursor.execute("""
    INSERT INTO movimentacoes (produto_id, lote_id, tipo, quantidade, usuario_id, motivo)
    VALUES (?, ?, 'ENTRADA', ?, ?, ?)
    """, (produto_id, lote_id, qtd, usuario_id, f"Recebimento Lote {numero_lote} (Validade: {data_validade})"))

    conn.commit()
    conn.close()
    return lote_id

def registrar_saida_venda(produto_id, quantidade, usuario_id=None, motivo="Venda Balcão"):
    """
    Registra a saída ou venda de produtos com baixa automática (RF05, RF06).
    Aplica o algoritmo FEFO (First Expired, First Out):
    - Prioriza os lotes com vencimento mais próximo que ainda estejam aptos para consumo.
    - Se o saldo total for insuficiente, a operação é rejeitada com mensagem clara.
    - Retorna a lista de baixas por lote efetuadas e se o produto atingiu o nível de reposição (RF08).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    qtd_solicitada = int(quantidade)
    if qtd_solicitada <= 0:
        conn.close()
        raise ValueError("A quantidade de saída deve ser maior que zero.")

    # Busca o produto e seu estoque mínimo
    prod = cursor.execute("SELECT id, nome, estoque_minimo FROM produtos WHERE id = ? AND ativo = 1", (produto_id,)).fetchone()
    if not prod:
        conn.close()
        raise ValueError("Produto não encontrado.")

    # Busca todos os lotes ativos com quantidade disponível, ordenados por data_validade ASC (FEFO)
    lotes_disponiveis = cursor.execute("""
        SELECT id, numero_lote, quantidade_atual, data_validade
        FROM lotes
        WHERE produto_id = ? AND quantidade_atual > 0
        ORDER BY data_validade ASC, id ASC
    """, (produto_id,)).fetchall()

    saldo_total = sum(l['quantidade_atual'] for l in lotes_disponiveis)
    if saldo_total < qtd_solicitada:
        conn.close()
        raise ValueError(f"Estoque insuficiente para '{prod['nome']}'. Solicitado: {qtd_solicitada}, Disponível em estoque: {saldo_total}.")

    restante_para_baixar = qtd_solicitada
    detalhes_baixas = []

    for lote in lotes_disponiveis:
        if restante_para_baixar <= 0:
            break

        disponivel_no_lote = lote['quantidade_atual']
        if disponivel_no_lote <= restante_para_baixar:
            baixar_neste_lote = disponivel_no_lote
        else:
            baixar_neste_lote = restante_para_baixar

        novo_saldo_lote = disponivel_no_lote - baixar_neste_lote
        restante_para_baixar -= baixar_neste_lote

        # Atualiza o lote
        cursor.execute("UPDATE lotes SET quantidade_atual = ? WHERE id = ?", (novo_saldo_lote, lote['id']))

        # Registra a movimentação individual daquele lote
        cursor.execute("""
        INSERT INTO movimentacoes (produto_id, lote_id, tipo, quantidade, usuario_id, motivo)
        VALUES (?, ?, 'SAIDA_VENDA', ?, ?, ?)
        """, (produto_id, lote['id'], baixar_neste_lote, usuario_id, f"{motivo} - Lote {lote['numero_lote']}"))

        detalhes_baixas.append({
            'lote_id': lote['id'],
            'numero_lote': lote['numero_lote'],
            'quantidade_baixada': baixar_neste_lote,
            'saldo_remanescente_lote': novo_saldo_lote,
            'data_validade': lote['data_validade']
        })

    conn.commit()

    # Verifica saldo final total do produto para disparar alerta de reposição (RF08)
    saldo_final_row = cursor.execute("SELECT COALESCE(SUM(quantidade_atual), 0) AS total FROM lotes WHERE produto_id = ?", (produto_id,)).fetchone()
    saldo_final = saldo_final_row['total']
    estoque_baixo = saldo_final <= prod['estoque_minimo']

    conn.close()

    return {
        'produto_id': produto_id,
        'produto_nome': prod['nome'],
        'quantidade_total_baixada': qtd_solicitada,
        'saldo_final_produto': saldo_final,
        'estoque_minimo': prod['estoque_minimo'],
        'alerta_reposicao': estoque_baixo,
        'detalhes_lotes': detalhes_baixas
    }

def descartar_lote(lote_id, motivo="Descarte por Vencimento/Avaria", usuario_id=None):
    """Realiza o descarte ou baixa por perda de um lote (ex: vencimento confirmado)."""
    conn = get_db_connection()
    cursor = conn.cursor()

    lote = cursor.execute("SELECT * FROM lotes WHERE id = ?", (lote_id,)).fetchone()
    if not lote:
        conn.close()
        raise ValueError("Lote não encontrado.")

    qtd = lote['quantidade_atual']
    if qtd <= 0:
        conn.close()
        raise ValueError("Este lote já está com quantidade zerada.")

    cursor.execute("UPDATE lotes SET quantidade_atual = 0 WHERE id = ?", (lote_id,))
    cursor.execute("""
    INSERT INTO movimentacoes (produto_id, lote_id, tipo, quantidade, usuario_id, motivo)
    VALUES (?, ?, 'DESCARTE_VENCIDO', ?, ?, ?)
    """, (lote['produto_id'], lote_id, qtd, usuario_id, motivo))

    conn.commit()
    conn.close()
    return qtd

def listar_lotes(produto_id=None, apenas_ativos=True):
    """Lista todos os lotes com status de validade calculado dinamicamente."""
    conn = get_db_connection()
    dias_alerta = int(obter_configuracao('dias_alerta_validade', 15))

    query = """
    SELECT 
        l.*, 
        p.nome AS produto_nome, 
        p.codigo_barras, 
        p.categoria, 
        p.unidade_medida
    FROM lotes l
    JOIN produtos p ON l.produto_id = p.id
    WHERE 1=1
    """
    params = []

    if produto_id:
        query += " AND l.produto_id = ?"
        params.append(produto_id)

    if apenas_ativos:
        query += " AND l.quantidade_atual > 0"

    query += " ORDER BY l.data_validade ASC"

    rows = conn.execute(query, params).fetchall()
    lotes = []

    for r in rows:
        item = dict(r)
        status_val, dias = calcular_status_validade(item['data_validade'], dias_alerta)
        item['status_validade'] = status_val
        item['dias_restantes'] = dias
        lotes.append(item)

    conn.close()
    return lotes

def obter_metricas_dashboard():
    """Calcula todas as estatísticas e KPIs principais para exibição no Dashboard."""
    conn = get_db_connection()
    dias_alerta = int(obter_configuracao('dias_alerta_validade', 15))
    hoje = date.today().isoformat()
    limite_alerta = (date.today() + timedelta(days=dias_alerta)).isoformat()

    # Total de produtos cadastrados
    total_produtos = conn.execute("SELECT COUNT(*) AS total FROM produtos WHERE ativo = 1").fetchone()['total']

    # Total de unidades em estoque
    total_itens = conn.execute("SELECT COALESCE(SUM(quantidade_atual), 0) AS total FROM lotes").fetchone()['total']

    # Valor total estimado do estoque (Preço Venda)
    valor_estoque_row = conn.execute("""
        SELECT COALESCE(SUM(l.quantidade_atual * p.preco_venda), 0) AS valor_total
        FROM lotes l
        JOIN produtos p ON l.produto_id = p.id
        WHERE p.ativo = 1 AND l.quantidade_atual > 0
    """).fetchone()
    valor_total_estoque = valor_estoque_row['valor_total']

    # Lotes Vencidos
    lotes_vencidos_row = conn.execute("""
        SELECT COUNT(*) AS total, COALESCE(SUM(quantidade_atual), 0) AS unidades
        FROM lotes
        WHERE data_validade < ? AND quantidade_atual > 0
    """, (hoje,)).fetchone()

    # Lotes Próximos do Vencimento
    lotes_proximos_row = conn.execute("""
        SELECT COUNT(*) AS total, COALESCE(SUM(quantidade_atual), 0) AS unidades
        FROM lotes
        WHERE data_validade >= ? AND data_validade <= ? AND quantidade_atual > 0
    """, (hoje, limite_alerta)).fetchone()

    # Produtos com Estoque Baixo ou Zerado
    produtos = listar_produtos()
    produtos_estoque_baixo = [p for p in produtos if p['status_estoque'] in ('BAIXO', 'ZERADO')]

    conn.close()

    return {
        'total_produtos': total_produtos,
        'total_itens_fisicos': total_itens,
        'valor_total_estoque': valor_total_estoque,
        'total_lotes_vencidos': lotes_vencidos_row['total'],
        'unidades_vencidas': lotes_vencidos_row['unidades'],
        'total_lotes_proximos': lotes_proximos_row['total'],
        'unidades_proximas': lotes_proximos_row['unidades'],
        'total_produtos_estoque_baixo': len(produtos_estoque_baixo),
        'produtos_estoque_baixo': produtos_estoque_baixo[:6],
        'dias_alerta_configurados': dias_alerta
    }

def listar_ultimas_movimentacoes(limite=10):
    """Retorna as movimentações mais recentes com detalhes completos."""
    conn = get_db_connection()
    rows = conn.execute(f"""
        SELECT 
            m.*,
            p.nome AS produto_nome,
            p.unidade_medida,
            l.numero_lote,
            l.data_validade,
            COALESCE(u.nome, 'Sistema') AS usuario_nome
        FROM movimentacoes m
        JOIN produtos p ON m.produto_id = p.id
        LEFT JOIN lotes l ON m.lote_id = l.id
        LEFT JOIN usuarios u ON m.usuario_id = u.id
        ORDER BY m.data_hora DESC
        LIMIT {int(limite)}
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- GESTÃO DE USUÁRIOS E FUNCIONÁRIOS (RBAC) ---

def listar_usuarios():
    """Retorna todos os usuários cadastrados com total de operações realizadas."""
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT 
            u.id, u.nome, u.email, u.perfil, u.cargo, u.ativo, u.criado_em,
            COUNT(m.id) AS total_operacoes
        FROM usuarios u
        LEFT JOIN movimentacoes m ON u.id = m.usuario_id
        GROUP BY u.id
        ORDER BY u.ativo DESC, u.nome ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def obter_usuario_por_id(usuario_id):
    """Obtém os dados de um usuário pelo ID."""
    conn = get_db_connection()
    row = conn.execute("SELECT id, nome, email, perfil, cargo, ativo, criado_em FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def cadastrar_usuario(nome, email, senha, perfil='estoquista', cargo='Colaborador'):
    """Cadastra um novo usuário corporativo no sistema com senha criptografada."""
    from werkzeug.security import generate_password_hash
    conn = get_db_connection()
    cursor = conn.cursor()

    email_limpo = email.strip().lower()
    existente = cursor.execute("SELECT id FROM usuarios WHERE email = ?", (email_limpo,)).fetchone()
    if existente:
        conn.close()
        raise ValueError(f"O e-mail '{email_limpo}' já está cadastrado para outro colaborador.")

    cursor.execute("""
    INSERT INTO usuarios (nome, email, senha_hash, perfil, cargo, ativo)
    VALUES (?, ?, ?, ?, ?, 1)
    """, (nome.strip(), email_limpo, generate_password_hash(senha), perfil, cargo.strip()))
    
    novo_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return novo_id

def editar_usuario(usuario_id, nome, email, perfil, cargo):
    """Atualiza dados cadastrais de um usuário."""
    conn = get_db_connection()
    cursor = conn.cursor()

    email_limpo = email.strip().lower()
    existente = cursor.execute("SELECT id FROM usuarios WHERE email = ? AND id != ?", (email_limpo, usuario_id)).fetchone()
    if existente:
        conn.close()
        raise ValueError(f"O e-mail '{email_limpo}' já está em uso por outro usuário.")

    cursor.execute("""
    UPDATE usuarios 
    SET nome = ?, email = ?, perfil = ?, cargo = ?
    WHERE id = ?
    """, (nome.strip(), email_limpo, perfil, cargo.strip(), usuario_id))
    
    conn.commit()
    conn.close()

def redefinir_senha_usuario(usuario_id, nova_senha):
    """Redefine a senha de um usuário pelo Administrador."""
    from werkzeug.security import generate_password_hash
    conn = get_db_connection()
    conn.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (generate_password_hash(nova_senha), usuario_id))
    conn.commit()
    conn.close()

def alternar_status_usuario(usuario_id, usuario_logado_id):
    """Ativa ou desativa o acesso de um usuário (não permite se auto-desativar)."""
    if int(usuario_id) == int(usuario_logado_id):
        raise ValueError("Você não pode desativar seu próprio usuário logado.")

    conn = get_db_connection()
    row = conn.execute("SELECT ativo FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    if not row:
        conn.close()
        raise ValueError("Usuário não encontrado.")

    novo_status = 0 if row['ativo'] == 1 else 1
    conn.execute("UPDATE usuarios SET ativo = ? WHERE id = ?", (novo_status, usuario_id))
    conn.commit()
    conn.close()
    return novo_status

def atualizar_perfil_proprio(usuario_id, nome, senha_atual, nova_senha=None):
    """Permite ao colaborador atualizar seu nome e, opcionalmente, trocar sua senha."""
    from werkzeug.security import check_password_hash, generate_password_hash
    conn = get_db_connection()
    user = conn.execute("SELECT senha_hash FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    if not user:
        conn.close()
        raise ValueError("Usuário não encontrado.")

    if not check_password_hash(user['senha_hash'], senha_atual):
        conn.close()
        raise ValueError("A senha atual informada está incorreta.")

    if nova_senha:
        conn.execute("UPDATE usuarios SET nome = ?, senha_hash = ? WHERE id = ?", 
                     (nome.strip(), generate_password_hash(nova_senha), usuario_id))
    else:
        conn.execute("UPDATE usuarios SET nome = ? WHERE id = ?", (nome.strip(), usuario_id))

    conn.commit()
    conn.close()

# --- MÓDULO DE FORNECEDORES (GESTÃO DE COMPRAS) ---

def listar_fornecedores(busca=None, apenas_ativos=False):
    """Lista os fornecedores cadastrados com contagem de lotes vinculados."""
    conn = get_db_connection()
    query = """
        SELECT 
            f.*,
            (SELECT COUNT(*) FROM lotes l WHERE l.fornecedor = f.nome_fantasia OR l.fornecedor = f.razao_social) AS total_lotes
        FROM fornecedores f
        WHERE 1=1
    """
    params = []

    if apenas_ativos:
        query += " AND f.ativo = 1"

    if busca:
        query += " AND (f.razao_social LIKE ? OR f.nome_fantasia LIKE ? OR f.cnpj LIKE ? OR f.cidade LIKE ?)"
        termo = f"%{busca}%"
        params.extend([termo, termo, termo, termo])

    query += " ORDER BY f.ativo DESC, f.razao_social ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def obter_fornecedor_por_id(fornecedor_id):
    """Obtém os dados completos de um fornecedor."""
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM fornecedores WHERE id = ?", (fornecedor_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def cadastrar_fornecedor(dados):
    """Cadastra um novo fornecedor homologado."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cnpj = dados.get('cnpj', '').strip() or None
    if cnpj:
        existente = cursor.execute("SELECT id FROM fornecedores WHERE cnpj = ?", (cnpj,)).fetchone()
        if existente:
            conn.close()
            raise ValueError(f"O CNPJ '{cnpj}' já está cadastrado para outro fornecedor.")

    cursor.execute("""
    INSERT INTO fornecedores (razao_social, nome_fantasia, cnpj, telefone, email, contato_responsavel, cidade, uf, observacoes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dados['razao_social'].strip(),
        dados.get('nome_fantasia', '').strip() or dados['razao_social'].strip(),
        cnpj,
        dados.get('telefone', '').strip(),
        dados.get('email', '').strip().lower(),
        dados.get('contato_responsavel', '').strip(),
        dados.get('cidade', '').strip(),
        dados.get('uf', '').strip().upper(),
        dados.get('observacoes', '').strip()
    ))
    novo_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return novo_id

def editar_fornecedor(fornecedor_id, dados):
    """Atualiza as informações de um fornecedor."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cnpj = dados.get('cnpj', '').strip() or None
    if cnpj:
        existente = cursor.execute("SELECT id FROM fornecedores WHERE cnpj = ? AND id != ?", (cnpj, fornecedor_id)).fetchone()
        if existente:
            conn.close()
            raise ValueError(f"O CNPJ '{cnpj}' já está cadastrado para outro fornecedor.")

    cursor.execute("""
    UPDATE fornecedores
    SET razao_social = ?, nome_fantasia = ?, cnpj = ?, telefone = ?,
        email = ?, contato_responsavel = ?, cidade = ?, uf = ?, observacoes = ?
    WHERE id = ?
    """, (
        dados['razao_social'].strip(),
        dados.get('nome_fantasia', '').strip() or dados['razao_social'].strip(),
        cnpj,
        dados.get('telefone', '').strip(),
        dados.get('email', '').strip().lower(),
        dados.get('contato_responsavel', '').strip(),
        dados.get('cidade', '').strip(),
        dados.get('uf', '').strip().upper(),
        dados.get('observacoes', '').strip(),
        fornecedor_id
    ))
    conn.commit()
    conn.close()

def alternar_status_fornecedor(fornecedor_id):
    """Ativa ou inativa um fornecedor comercial."""
    conn = get_db_connection()
    row = conn.execute("SELECT ativo FROM fornecedores WHERE id = ?", (fornecedor_id,)).fetchone()
    if not row:
        conn.close()
        raise ValueError("Fornecedor não encontrado.")

    novo_status = 0 if row['ativo'] == 1 else 1
    conn.execute("UPDATE fornecedores SET ativo = ? WHERE id = ?", (novo_status, fornecedor_id))
    conn.commit()
    conn.close()
    return novo_status

# --- MÓDULO DE RELATÓRIOS E EXPORTAÇÕES EMPRESARIAIS ---

def obter_relatorio_inventario():
    """Retorna dados consolidados para o relatório de inventário de estoque."""
    produtos = listar_produtos()
    linhas = []
    total_custo = 0.0
    total_venda = 0.0

    for p in produtos:
        custo_total_item = p['estoque_atual'] * p['preco_custo']
        venda_total_item = p['estoque_atual'] * p['preco_venda']
        total_custo += custo_total_item
        total_venda += venda_total_item

        linhas.append({
            'id': p['id'],
            'codigo_barras': p['codigo_barras'] or 'S/N',
            'nome': p['nome'],
            'categoria': p['categoria'],
            'unidade': p['unidade_medida'],
            'estoque_atual': p['estoque_atual'],
            'estoque_minimo': p['estoque_minimo'],
            'status_estoque': p['status_estoque'],
            'status_validade': p.get('status_validade_geral', 'OK'),
            'dias_validade': p.get('dias_validade_proxima'),
            'preco_custo': p['preco_custo'],
            'preco_venda': p['preco_venda'],
            'valor_custo_total': custo_total_item,
            'valor_venda_total': venda_total_item
        })

    return {
        'itens': linhas,
        'total_produtos': len(linhas),
        'total_unidades': sum(l['estoque_atual'] for l in linhas),
        'valor_total_custo': total_custo,
        'valor_total_venda': total_venda
    }

def obter_relatorio_perdas():
    """Retorna o histórico de todas as perdas e descartes por vencimento com prejuízo calculado."""
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT 
            m.id,
            m.data_hora,
            m.quantidade,
            m.motivo,
            p.nome AS produto_nome,
            p.codigo_barras,
            p.categoria,
            p.unidade_medida,
            p.preco_custo,
            l.numero_lote,
            l.data_validade,
            l.fornecedor,
            COALESCE(u.nome, 'Sistema') AS usuario_nome
        FROM movimentacoes m
        JOIN produtos p ON m.produto_id = p.id
        LEFT JOIN lotes l ON m.lote_id = l.id
        LEFT JOIN usuarios u ON m.usuario_id = u.id
        WHERE m.tipo = 'DESCARTE_VENCIDO'
        ORDER BY m.data_hora DESC
    """).fetchall()
    conn.close()

    itens = []
    total_prejuizo = 0.0
    total_unidades_perdidas = 0

    for r in rows:
        d = dict(r)
        prejuizo_item = d['quantidade'] * d['preco_custo']
        d['prejuizo_financeiro'] = prejuizo_item
        total_prejuizo += prejuizo_item
        total_unidades_perdidas += d['quantidade']
        itens.append(d)

    return {
        'itens': itens,
        'total_descartes': len(itens),
        'total_unidades_perdidas': total_unidades_perdidas,
        'prejuizo_total': total_prejuizo
    }

def obter_relatorio_compras():
    """Retorna itens com estoque baixo ou zerado e cálculo da sugestão de compra."""
    produtos = listar_produtos()
    criticos = [p for p in produtos if p['status_estoque'] in ('BAIXO', 'ZERADO')]

    itens = []
    total_orcado = 0.0

    conn = get_db_connection()
    for p in criticos:
        deficit = max(0, p['estoque_minimo'] - p['estoque_atual'])
        # Sugestão de pedido: cobrir o déficit + 1x estoque mínimo para margem de giro
        sugestao_compra = deficit + p['estoque_minimo']
        custo_previsto = sugestao_compra * p['preco_custo']
        total_orcado += custo_previsto

        # Busca último fornecedor associado aos lotes deste produto
        ultimo_lote = conn.execute("""
            SELECT fornecedor FROM lotes 
            WHERE produto_id = ? AND fornecedor IS NOT NULL AND fornecedor != ''
            ORDER BY id DESC LIMIT 1
        """, (p['id'],)).fetchone()
        fornecedor_sugerido = ultimo_lote['fornecedor'] if ultimo_lote else 'Não definido'

        itens.append({
            'produto_id': p['id'],
            'nome': p['nome'],
            'codigo_barras': p['codigo_barras'] or 'S/N',
            'categoria': p['categoria'],
            'unidade': p['unidade_medida'],
            'saldo_atual': p['estoque_atual'],
            'estoque_minimo': p['estoque_minimo'],
            'deficit': deficit,
            'sugestao_compra': sugestao_compra,
            'preco_custo': p['preco_custo'],
            'custo_total_previsto': custo_previsto,
            'fornecedor_sugerido': fornecedor_sugerido
        })
    conn.close()

    return {
        'itens': itens,
        'total_itens_repor': len(itens),
        'total_unidades_compra': sum(i['sugestao_compra'] for i in itens),
        'valor_total_orcado': total_orcado
    }




