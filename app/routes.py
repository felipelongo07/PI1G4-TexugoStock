from functools import wraps
import csv
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, Response
from werkzeug.security import check_password_hash
from datetime import date
from app.database import get_db_connection
from app.models import (
    listar_produtos, obter_produto_por_id, cadastrar_produto, editar_produto, excluir_produto,
    registrar_entrada_lote, registrar_saida_venda, descartar_lote, listar_lotes,
    obter_metricas_dashboard, listar_ultimas_movimentacoes, obter_configuracao, atualizar_configuracao,
    listar_usuarios, obter_usuario_por_id, cadastrar_usuario, editar_usuario, redefinir_senha_usuario,
    alternar_status_usuario, atualizar_perfil_proprio,
    listar_fornecedores, obter_fornecedor_por_id, cadastrar_fornecedor, editar_fornecedor, alternar_status_fornecedor,
    obter_relatorio_inventario, obter_relatorio_perdas, obter_relatorio_compras
)

main_bp = Blueprint('main', __name__)

# --- DECORATORS DE AUTENTICAÃ‡ÃƒO E PERMISSÃƒO (RNF05) ---

def login_required(f):
    """Garante que a rota sÃ³ pode ser acessada por usuÃ¡rios autenticados."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Por favor, faÃ§a login para acessar esta funcionalidade.', 'warning')
            return redirect(url_for('main.login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Garante que a rota sÃ³ pode ser acessada pelo Administrador/Gestor (RNF05)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('FaÃ§a login como Administrador para continuar.', 'warning')
            return redirect(url_for('main.login', next=request.path))
        if session['usuario']['perfil'] != 'admin':
            flash('Acesso restrito ao perfil de Administrador/Gestor.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROTAS DE AUTENTICAÃ‡ÃƒO ---

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Tela e processamento de login de usuÃ¡rios."""
    if 'usuario' in session:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM usuarios WHERE email = ? AND ativo = 1", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['senha_hash'], senha):
            session['usuario'] = {
                'id': user['id'],
                'nome': user['nome'],
                'email': user['email'],
                'perfil': user['perfil'],
                'cargo': user['cargo']
            }
            flash(f"Bem-vindo(a) de volta, {user['nome']}!", 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('E-mail ou senha incorretos. Tente novamente.', 'danger')

    return render_template('login.html')

@main_bp.route('/logout')
def logout():
    """Encerra a sessÃ£o atual do usuÃ¡rio."""
    session.pop('usuario', None)
    flash('VocÃª saiu do sistema com seguranÃ§a.', 'info')
    return redirect(url_for('main.login'))

# --- ROTA INICIAL / DASHBOARD ---

@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Tela principal do sistema com mÃ©tricas, alertas e visÃ£o geral."""
    metricas = obter_metricas_dashboard()
    ultimas_movs = listar_ultimas_movimentacoes(limite=8)
    lotes_criticos = listar_lotes(apenas_ativos=True)
    # Filtra apenas lotes que estejam vencidos ou prÃ³ximos de vencer
    lotes_alertas = [l for l in lotes_criticos if l['status_validade'] in ('VENCIDO', 'PROXIMO')][:8]
    
    return render_template('dashboard.html', 
                           metricas=metricas, 
                           movimentacoes=ultimas_movs, 
                           lotes_alertas=lotes_alertas)

# --- MÃ“DULO DE PRODUTOS (RF01, RF04, RNF03) ---

@main_bp.route('/produtos')
@login_required
def produtos():
    """Consulta e catÃ¡logo geral de produtos com estoque em tempo real (RF04)."""
    busca = request.args.get('busca', '').strip()
    categoria = request.args.get('categoria', '').strip()
    status_filtro = request.args.get('status', '').strip()

    lista = listar_produtos(busca=busca or None, categoria=categoria or None, status_filtro=status_filtro or None)

    # Obter lista de categorias existentes para o filtro
    conn = get_db_connection()
    cats = conn.execute("SELECT DISTINCT categoria FROM produtos WHERE ativo = 1 ORDER BY categoria ASC").fetchall()
    conn.close()
    categorias_disponiveis = [c['categoria'] for c in cats]

    total_produtos = len(lista)
    total_baixo = sum(1 for p in lista if p['status_estoque'] in ('BAIXO', 'ZERADO'))

    return render_template('produtos.html', 
                           produtos=lista, 
                           busca=busca, 
                           categoria_selecionada=categoria, 
                           status_selecionado=status_filtro,
                           categorias=categorias_disponiveis,
                           total_produtos=total_produtos,
                           total_baixo=total_baixo)

@main_bp.route('/produtos/novo', methods=['GET', 'POST'])
@login_required
def novo_produto():
    """FormulÃ¡rio para cadastrar novos produtos com validaÃ§Ã£o de dados obrigatÃ³rios (RF01, RNF03)."""
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        categoria = request.form.get('categoria', '').strip()
        codigo_barras = request.form.get('codigo_barras', '').strip()
        unidade_medida = request.form.get('unidade_medida', 'UN').strip()
        preco_custo = request.form.get('preco_custo', '0').strip()
        preco_venda = request.form.get('preco_venda', '0').strip()
        estoque_minimo = request.form.get('estoque_minimo', '5').strip()
        descricao = request.form.get('descricao', '').strip()

        # ValidaÃ§Ãµes de campos obrigatÃ³rios (RNF03)
        if not nome:
            flash('O nome do produto Ã© obrigatÃ³rio!', 'danger')
            return render_template('produto_form.html', modo='novo', form=request.form)

        if not categoria:
            flash('Selecione ou informe a categoria do produto!', 'danger')
            return render_template('produto_form.html', modo='novo', form=request.form)

        try:
            estoque_min_val = int(estoque_minimo)
            if estoque_min_val < 0:
                raise ValueError()
        except ValueError:
            flash('O estoque mÃ­nimo deve ser um nÃºmero inteiro igual ou superior a zero.', 'danger')
            return render_template('produto_form.html', modo='novo', form=request.form)

        try:
            preco_custo_val = float(preco_custo.replace(',', '.')) if preco_custo else 0.0
            preco_venda_val = float(preco_venda.replace(',', '.')) if preco_venda else 0.0
        except ValueError:
            flash('Informe valores numÃ©ricos vÃ¡lidos para os preÃ§os.', 'danger')
            return render_template('produto_form.html', modo='novo', form=request.form)

        # Verifica cÃ³digo de barras duplicado se informado
        if codigo_barras:
            conn = get_db_connection()
            existente = conn.execute("SELECT id FROM produtos WHERE codigo_barras = ? AND ativo = 1", (codigo_barras,)).fetchone()
            conn.close()
            if existente:
                flash(f'O cÃ³digo de barras "{codigo_barras}" jÃ¡ estÃ¡ cadastrado para outro produto!', 'danger')
                return render_template('produto_form.html', modo='novo', form=request.form)

        dados = {
            'nome': nome,
            'categoria': categoria,
            'codigo_barras': codigo_barras,
            'unidade_medida': unidade_medida,
            'preco_custo': preco_custo_val,
            'preco_venda': preco_venda_val,
            'estoque_minimo': estoque_min_val,
            'descricao': descricao
        }

        novo_id = cadastrar_produto(dados)
        flash(f'Produto "{nome}" cadastrado com sucesso!', 'success')
        
        # Oferece a opÃ§Ã£o de jÃ¡ dar entrada no primeiro lote
        return redirect(url_for('main.entrada_lote', produto_id=novo_id))

    return render_template('produto_form.html', modo='novo', form={})

@main_bp.route('/produtos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_produto_rota(id):
    """EdiÃ§Ã£o das informaÃ§Ãµes e parÃ¢metros de um produto."""
    produto = obter_produto_por_id(id)
    if not produto:
        flash('Produto nÃ£o encontrado.', 'danger')
        return redirect(url_for('main.produtos'))

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        categoria = request.form.get('categoria', '').strip()
        codigo_barras = request.form.get('codigo_barras', '').strip()
        unidade_medida = request.form.get('unidade_medida', 'UN').strip()
        preco_custo = request.form.get('preco_custo', '0').strip()
        preco_venda = request.form.get('preco_venda', '0').strip()
        estoque_minimo = request.form.get('estoque_minimo', '5').strip()
        descricao = request.form.get('descricao', '').strip()

        if not nome or not categoria:
            flash('Nome e Categoria sÃ£o campos obrigatÃ³rios.', 'danger')
            return render_template('produto_form.html', modo='editar', produto=produto, form=request.form)

        try:
            estoque_min_val = int(estoque_minimo)
            preco_custo_val = float(preco_custo.replace(',', '.')) if preco_custo else 0.0
            preco_venda_val = float(preco_venda.replace(',', '.')) if preco_venda else 0.0
        except ValueError:
            flash('Preencha os valores numÃ©ricos corretamente.', 'danger')
            return render_template('produto_form.html', modo='editar', produto=produto, form=request.form)

        dados = {
            'nome': nome,
            'categoria': categoria,
            'codigo_barras': codigo_barras,
            'unidade_medida': unidade_medida,
            'preco_custo': preco_custo_val,
            'preco_venda': preco_venda_val,
            'estoque_minimo': estoque_min_val,
            'descricao': descricao
        }

        editar_produto(id, dados)
        flash(f'Produto "{nome}" atualizado com sucesso!', 'success')
        return redirect(url_for('main.produto_detalhe', id=id))

    return render_template('produto_form.html', modo='editar', produto=produto, form=produto)

@main_bp.route('/produtos/<int:id>')
@login_required
def produto_detalhe(id):
    """VisÃ£o 360Âº de um produto especÃ­fico com seus lotes ativos e histÃ³rico."""
    produto = obter_produto_por_id(id)
    if not produto:
        flash('Produto nÃ£o encontrado.', 'danger')
        return redirect(url_for('main.produtos'))

    lotes = listar_lotes(produto_id=id, apenas_ativos=False)
    
    # HistÃ³rico de movimentaÃ§Ãµes deste produto
    conn = get_db_connection()
    movs = conn.execute("""
        SELECT m.*, l.numero_lote, COALESCE(u.nome, 'Sistema') AS usuario_nome
        FROM movimentacoes m
        LEFT JOIN lotes l ON m.lote_id = l.id
        LEFT JOIN usuarios u ON m.usuario_id = u.id
        WHERE m.produto_id = ?
        ORDER BY m.data_hora DESC
        LIMIT 15
    """, (id,)).fetchall()
    conn.close()

    return render_template('produto_detalhe.html', produto=produto, lotes=lotes, movimentacoes=[dict(m) for m in movs])

@main_bp.route('/produtos/excluir/<int:id>', methods=['POST'])
@admin_required
def excluir_produto_rota(id):
    """DesativaÃ§Ã£o de um produto (exclusivo para perfil Administrador)."""
    produto = obter_produto_por_id(id)
    if produto:
        excluir_produto(id)
        flash(f'Produto "{produto["nome"]}" foi removido do catÃ¡logo.', 'success')
    return redirect(url_for('main.produtos'))

# --- MÃ“DULO DE RECEBIMENTO / ENTRADA DE LOTES (RF02, RF03) ---

@main_bp.route('/entradas', methods=['GET', 'POST'])
@main_bp.route('/entrada-lote', methods=['GET', 'POST'])
@login_required
def entrada_lote():
    """Registro de recebimento de mercadorias no estoque com lote e validade (RF02, RF03)."""
    produto_id_pre = request.args.get('produto_id')
    
    if request.method == 'POST':
        try:
            prod_id = int(request.form.get('produto_id'))
            numero_lote = request.form.get('numero_lote', '').strip()
            quantidade = int(request.form.get('quantidade', 0))
            data_validade = request.form.get('data_validade', '').strip()
            fornecedor = request.form.get('fornecedor', '').strip()
            observacoes = request.form.get('observacoes', '').strip()

            if not numero_lote or not data_validade:
                flash('NÃºmero do lote e data de validade sÃ£o obrigatÃ³rios!', 'danger')
                return redirect(url_for('main.entrada_lote', produto_id=prod_id))

            if quantidade <= 0:
                flash('A quantidade recebida deve ser maior que zero!', 'danger')
                return redirect(url_for('main.entrada_lote', produto_id=prod_id))

            usuario_id = session.get('usuario', {}).get('id')
            registrar_entrada_lote(
                produto_id=prod_id,
                numero_lote=numero_lote,
                quantidade=quantidade,
                data_validade=data_validade,
                fornecedor=fornecedor,
                observacoes=observacoes,
                usuario_id=usuario_id
            )

            prod = obter_produto_por_id(prod_id)
            flash(f"Entrada registrada com sucesso! Lote '{numero_lote}' com {quantidade} un. adicionado a '{prod['nome']}'.", 'success')
            return redirect(url_for('main.produto_detalhe', id=prod_id))

        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            flash(f'Erro ao processar entrada: {str(e)}', 'danger')

    produtos_lista = listar_produtos()
    fornecedores_lista = listar_fornecedores(apenas_ativos=True)
    return render_template('entrada_lote.html', 
                           produtos=produtos_lista, 
                           fornecedores=fornecedores_lista,
                           produto_id_selecionado=produto_id_pre)

# --- MÃ“DULO DE SAÃDAS / VENDAS COM ALGORITMO FEFO (RF05, RF06, RF08) ---

@main_bp.route('/saidas', methods=['GET', 'POST'])
@main_bp.route('/saida-venda', methods=['GET', 'POST'])
@login_required
def saida_venda():
    """Registro de saÃ­da ou venda de produto com baixa automÃ¡tica e FEFO (RF05, RF06)."""
    produto_id_pre = request.args.get('produto_id')

    if request.method == 'POST':
        try:
            prod_id = int(request.form.get('produto_id'))
            quantidade = int(request.form.get('quantidade', 0))
            motivo = request.form.get('motivo', 'Venda BalcÃ£o').strip()

            usuario_id = session.get('usuario', {}).get('id')
            resultado = registrar_saida_venda(
                produto_id=prod_id,
                quantidade=quantidade,
                usuario_id=usuario_id,
                motivo=motivo
            )

            msg = f"SaÃ­da de {quantidade} un. de '{resultado['produto_nome']}' realizada com sucesso via algoritmo FEFO!"
            if resultado['alerta_reposicao']:
                flash(f"{msg} âš ï¸ ATENÃ‡ÃƒO: Saldo atual ({resultado['saldo_final_produto']}) atingiu o estoque mÃ­nimo ({resultado['estoque_minimo']})! ReposiÃ§Ã£o necessÃ¡ria.", 'warning')
            else:
                flash(msg, 'success')

            return redirect(url_for('main.produto_detalhe', id=prod_id))

        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            flash(f'Erro ao processar saÃ­da: {str(e)}', 'danger')

    produtos_lista = listar_produtos()
    return render_template('saida_venda.html', produtos=produtos_lista, produto_id_selecionado=produto_id_pre)

# --- MÃ“DULO DE CONTROLE DE VALIDADE E DESCARTE (RF07) ---

@main_bp.route('/validade')
@main_bp.route('/controle-validade')
@login_required
def controle_validade():
    """Painel detalhado de lotes e alertas de validade (RF07)."""
    filtro_status = request.args.get('status', 'TODOS')
    lotes = listar_lotes(apenas_ativos=True)

    if filtro_status == 'VENCIDO':
        lotes = [l for l in lotes if l['status_validade'] == 'VENCIDO']
    elif filtro_status == 'PROXIMO':
        lotes = [l for l in lotes if l['status_validade'] == 'PROXIMO']
    elif filtro_status == 'OK':
        lotes = [l for l in lotes if l['status_validade'] == 'OK']

    return render_template('controle_validade.html', lotes=lotes, status_filtro=filtro_status)

@main_bp.route('/lotes/descartar/<int:id>', methods=['POST'])
@login_required
def descarte_lote_rota(id):
    """Baixa por descarte de produto vencido ou avariado."""
    motivo = request.form.get('motivo', 'Descarte por Vencimento').strip()
    usuario_id = session.get('usuario', {}).get('id')
    try:
        qtd = descartar_lote(id, motivo=motivo, usuario_id=usuario_id)
        flash(f'Lote baixado por descarte com sucesso ({qtd} unidades descartadas).', 'info')
    except Exception as e:
        flash(f'Erro ao descartar lote: {str(e)}', 'danger')
    return redirect(request.referrer or url_for('main.controle_validade'))

# --- MÃ“DULO DE ALERTAS DE ESTOQUE BAIXO (RF08) ---

@main_bp.route('/estoque-baixo')
@login_required
def estoque_baixo():
    """Painel de produtos que atingiram nÃ­vel crÃ­tico para reposiÃ§Ã£o (RF08)."""
    produtos = listar_produtos()
    produtos_criticos = [p for p in produtos if p['status_estoque'] in ('BAIXO', 'ZERADO')]
    return render_template('estoque_baixo.html', produtos=produtos_criticos)

# --- AUDITORIA E HISTÃ“RICO DE MOVIMENTAÃ‡Ã•ES ---

@main_bp.route('/movimentacoes')
@login_required
def movimentacoes():
    """HistÃ³rico completo de auditoria das entradas, saÃ­das e descartes."""
    historico = listar_ultimas_movimentacoes(limite=50)
    return render_template('movimentacoes.html', movimentacoes=historico)

# --- CONFIGURAÃ‡Ã•ES EMPRESARIAIS (RNF05 / ADMIN) ---

@main_bp.route('/configuracoes', methods=['GET', 'POST'])
@admin_required
def configuracoes():
    """Ajuste de parÃ¢metros da empresa e regras de negÃ³cio de validade."""
    if request.method == 'POST':
        # Dados da Empresa
        empresa_nome = request.form.get('empresa_nome', '').strip()
        empresa_cnpj = request.form.get('empresa_cnpj', '').strip()
        empresa_telefone = request.form.get('empresa_telefone', '').strip()
        empresa_email = request.form.get('empresa_email', '').strip()
        empresa_endereco = request.form.get('empresa_endereco', '').strip()

        if empresa_nome:
            atualizar_configuracao('empresa_nome', empresa_nome)
        if empresa_cnpj:
            atualizar_configuracao('empresa_cnpj', empresa_cnpj)
        if empresa_telefone:
            atualizar_configuracao('empresa_telefone', empresa_telefone)
        if empresa_email:
            atualizar_configuracao('empresa_email', empresa_email)
        if empresa_endereco:
            atualizar_configuracao('empresa_endereco', empresa_endereco)

        # Regras de NegÃ³cio
        dias = request.form.get('dias_alerta_validade', '15').strip()
        try:
            dias_val = int(dias)
            if dias_val <= 0:
                raise ValueError()
            atualizar_configuracao('dias_alerta_validade', str(dias_val))
            flash('ConfiguraÃ§Ãµes da empresa e parÃ¢metros atualizados com sucesso!', 'success')
        except ValueError:
            flash('Informe um nÃºmero inteiro vÃ¡lido maior que zero para o alerta de validade.', 'danger')

    dias_alerta = obter_configuracao('dias_alerta_validade', '15')
    dados_empresa = {
        'nome': obter_configuracao('empresa_nome', 'Texugo ComÃ©rcio & DistribuiÃ§Ã£o Ltda.'),
        'cnpj': obter_configuracao('empresa_cnpj', '12.345.678/0001-90'),
        'telefone': obter_configuracao('empresa_telefone', '(11) 3456-7890'),
        'email': obter_configuracao('empresa_email', 'contato@texugostock.com'),
        'endereco': obter_configuracao('empresa_endereco', 'Av. Empresarial, 1000 - Centro')
    }
    return render_template('configuracoes.html', dias_alerta=dias_alerta, empresa=dados_empresa)

# --- MÃ“DULO DE GESTÃƒO DE USUÃRIOS E COLABORADORES (ADMIN) ---

@main_bp.route('/usuarios')
@admin_required
def usuarios():
    """Painel de colaboradores e gestÃ£o de acessos corporativos."""
    lista = listar_usuarios()
    return render_template('usuarios.html', usuarios=lista)

@main_bp.route('/usuarios/novo', methods=['POST'])
@admin_required
def novo_usuario():
    """Cadastra um novo colaborador no sistema."""
    nome = request.form.get('nome', '').strip()
    email = request.form.get('email', '').strip().lower()
    senha = request.form.get('senha', '')
    perfil = request.form.get('perfil', 'estoquista')
    cargo = request.form.get('cargo', 'Colaborador').strip()

    if not nome or not email or not senha:
        flash('Nome, e-mail e senha inicial sÃ£o obrigatÃ³rios.', 'danger')
        return redirect(url_for('main.usuarios'))

    if len(senha) < 6:
        flash('A senha deve ter pelo menos 6 caracteres.', 'danger')
        return redirect(url_for('main.usuarios'))

    try:
        cadastrar_usuario(nome, email, senha, perfil, cargo)
        flash(f"Colaborador '{nome}' cadastrado com sucesso!", 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    except Exception as e:
        flash(f"Erro ao cadastrar usuÃ¡rio: {str(e)}", 'danger')

    return redirect(url_for('main.usuarios'))

@main_bp.route('/usuarios/editar/<int:id>', methods=['POST'])
@admin_required
def editar_usuario_rota(id):
    """Atualiza dados de um colaborador."""
    nome = request.form.get('nome', '').strip()
    email = request.form.get('email', '').strip().lower()
    perfil = request.form.get('perfil', 'estoquista')
    cargo = request.form.get('cargo', 'Colaborador').strip()

    if not nome or not email:
        flash('Nome e e-mail sÃ£o obrigatÃ³rios.', 'danger')
        return redirect(url_for('main.usuarios'))

    try:
        editar_usuario(id, nome, email, perfil, cargo)
        flash(f"Colaborador '{nome}' atualizado com sucesso!", 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    except Exception as e:
        flash(f"Erro ao atualizar: {str(e)}", 'danger')

    return redirect(url_for('main.usuarios'))

@main_bp.route('/usuarios/redefinir-senha/<int:id>', methods=['POST'])
@admin_required
def redefinir_senha_rota(id):
    """Redefine a senha de um colaborador pelo Administrador."""
    nova_senha = request.form.get('nova_senha', '')
    if not nova_senha or len(nova_senha) < 6:
        flash('A nova senha deve ter no mÃ­nimo 6 caracteres.', 'danger')
        return redirect(url_for('main.usuarios'))

    try:
        redefinir_senha_usuario(id, nova_senha)
        flash('Senha redefinida com sucesso!', 'success')
    except Exception as e:
        flash(f"Erro ao redefinir senha: {str(e)}", 'danger')

    return redirect(url_for('main.usuarios'))

@main_bp.route('/usuarios/status/<int:id>', methods=['POST'])
@admin_required
def alternar_status_usuario_rota(id):
    """Ativa ou desativa um usuÃ¡rio no sistema."""
    usuario_logado_id = session.get('usuario', {}).get('id')
    try:
        novo_status = alternar_status_usuario(id, usuario_logado_id)
        msg = "UsuÃ¡rio ATIVADO com sucesso!" if novo_status == 1 else "UsuÃ¡rio DESATIVADO (acesso bloqueado)."
        flash(msg, 'info')
    except ValueError as e:
        flash(str(e), 'danger')
    except Exception as e:
        flash(f"Erro ao alterar status: {str(e)}", 'danger')

    return redirect(url_for('main.usuarios'))

# --- MEU PERFIL (QUALQUER USUÃRIO LOGADO) ---

@main_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def perfil():
    """Tela para o colaborador visualizar seus dados e alterar sua senha."""
    usuario_id = session['usuario']['id']

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        senha_atual = request.form.get('senha_atual', '')
        nova_senha = request.form.get('nova_senha', '')
        confirmacao = request.form.get('confirmacao_senha', '')

        if not nome or not senha_atual:
            flash('Nome e senha atual sÃ£o obrigatÃ³rios.', 'danger')
            return redirect(url_for('main.perfil'))

        if nova_senha:
            if len(nova_senha) < 6:
                flash('A nova senha deve ter no mÃ­nimo 6 caracteres.', 'danger')
                return redirect(url_for('main.perfil'))
            if nova_senha != confirmacao:
                flash('A confirmaÃ§Ã£o da nova senha nÃ£o confere.', 'danger')
                return redirect(url_for('main.perfil'))

        try:
            atualizar_perfil_proprio(usuario_id, nome, senha_atual, nova_senha or None)
            session['usuario']['nome'] = nome
            flash('Perfil atualizado com sucesso!', 'success')
            return redirect(url_for('main.perfil'))
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            flash(f"Erro ao atualizar perfil: {str(e)}", 'danger')

    dados_usuario = obter_usuario_por_id(usuario_id)
    return render_template('perfil.html', usuario=dados_usuario)


# --- MÓDULO DE FORNECEDORES (GESTÃO DE COMPRAS) ---

@main_bp.route('/fornecedores')
@login_required
def fornecedores():
    """Painel de parceiros e fornecedores comerciais homologados."""
    busca = request.args.get('busca', '').strip()
    lista = listar_fornecedores(busca=busca or None)
    return render_template('fornecedores.html', fornecedores=lista, busca=busca)

@main_bp.route('/fornecedores/novo', methods=['POST'])
@login_required
def novo_fornecedor():
    """Cadastra um novo fornecedor homologado."""
    razao_social = request.form.get('razao_social', '').strip()
    nome_fantasia = request.form.get('nome_fantasia', '').strip()
    cnpj = request.form.get('cnpj', '').strip()
    telefone = request.form.get('telefone', '').strip()
    email = request.form.get('email', '').strip()
    contato = request.form.get('contato_responsavel', '').strip()
    cidade = request.form.get('cidade', '').strip()
    uf = request.form.get('uf', '').strip()
    observacoes = request.form.get('observacoes', '').strip()

    if not razao_social:
        flash('Razão Social ou Nome do fornecedor é obrigatório.', 'danger')
        return redirect(url_for('main.fornecedores'))

    dados = {
        'razao_social': razao_social,
        'nome_fantasia': nome_fantasia or razao_social,
        'cnpj': cnpj,
        'telefone': telefone,
        'email': email,
        'contato_responsavel': contato,
        'cidade': cidade,
        'uf': uf,
        'observacoes': observacoes
    }

    try:
        cadastrar_fornecedor(dados)
        flash(f"Fornecedor '{razao_social}' cadastrado com sucesso!", 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    except Exception as e:
        flash(f"Erro ao cadastrar fornecedor: {str(e)}", 'danger')

    return redirect(url_for('main.fornecedores'))

@main_bp.route('/fornecedores/editar/<int:id>', methods=['POST'])
@login_required
def editar_fornecedor_rota(id):
    """Atualiza as informações de um fornecedor cadastrado."""
    razao_social = request.form.get('razao_social', '').strip()
    nome_fantasia = request.form.get('nome_fantasia', '').strip()
    cnpj = request.form.get('cnpj', '').strip()
    telefone = request.form.get('telefone', '').strip()
    email = request.form.get('email', '').strip()
    contato = request.form.get('contato_responsavel', '').strip()
    cidade = request.form.get('cidade', '').strip()
    uf = request.form.get('uf', '').strip()
    observacoes = request.form.get('observacoes', '').strip()

    if not razao_social:
        flash('Razão Social é obrigatória.', 'danger')
        return redirect(url_for('main.fornecedores'))

    dados = {
        'razao_social': razao_social,
        'nome_fantasia': nome_fantasia or razao_social,
        'cnpj': cnpj,
        'telefone': telefone,
        'email': email,
        'contato_responsavel': contato,
        'cidade': cidade,
        'uf': uf,
        'observacoes': observacoes
    }

    try:
        editar_fornecedor(id, dados)
        flash(f"Fornecedor '{razao_social}' atualizado com sucesso!", 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    except Exception as e:
        flash(f"Erro ao atualizar fornecedor: {str(e)}", 'danger')

    return redirect(url_for('main.fornecedores'))

@main_bp.route('/fornecedores/status/<int:id>', methods=['POST'])
@login_required
def alternar_status_fornecedor_rota(id):
    """Ativa ou desativa um fornecedor homologado."""
    try:
        novo_status = alternar_status_fornecedor(id)
        msg = "Fornecedor ATIVADO com sucesso!" if novo_status == 1 else "Fornecedor INATIVADO para novas compras."
        flash(msg, 'info')
    except ValueError as e:
        flash(str(e), 'danger')
    except Exception as e:
        flash(f"Erro ao alterar status: {str(e)}", 'danger')

    return redirect(url_for('main.fornecedores'))

# --- MÓDULO DE RELATÓRIOS E EXPORTAÇÕES EXCEL / CSV ---

@main_bp.route('/relatorios')
@login_required
def relatorios():
    """Central de relatórios gerenciais e pré-visualização das exportações."""
    inv = obter_relatorio_inventario()
    perdas = obter_relatorio_perdas()
    compras = obter_relatorio_compras()
    return render_template('relatorios.html', inventario=inv, perdas=perdas, compras=compras)

@main_bp.route('/relatorios/exportar/inventario')
@login_required
def exportar_inventario_csv():
    """Gera download do inventário completo em formato CSV compatível com Excel."""
    dados = obter_relatorio_inventario()
    output = io.StringIO()
    # Adiciona BOM UTF-8 para o Excel abrir caracteres especiais com acentos perfeitamente
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)

    # Cabeçalho
    writer.writerow([
        'ID', 'Código de Barras', 'Produto', 'Categoria', 'Unidade',
        'Estoque Atual', 'Estoque Mínimo', 'Status Estoque', 'Status Validade',
        'Dias até Vencer', 'Preço Custo (R$)', 'Preço Venda (R$)',
        'Total em Custo (R$)', 'Total em Venda (R$)'
    ])

    for i in dados['itens']:
        writer.writerow([
            i['id'],
            i['codigo_barras'],
            i['nome'],
            i['categoria'],
            i['unidade'],
            i['estoque_atual'],
            i['estoque_minimo'],
            i['status_estoque'],
            i['status_validade'],
            i['dias_validade'] if i['dias_validade'] is not None else '-',
            f"{i['preco_custo']:.2f}".replace('.', ','),
            f"{i['preco_venda']:.2f}".replace('.', ','),
            f"{i['valor_custo_total']:.2f}".replace('.', ','),
            f"{i['valor_venda_total']:.2f}".replace('.', ',')
        ])

    hoje = date.today().isoformat()
    nome_arquivo = f"inventario_estoque_{hoje}.csv"
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={nome_arquivo}"}
    )

@main_bp.route('/relatorios/exportar/perdas')
@login_required
def exportar_perdas_csv():
    """Gera download do histórico de perdas/descartes por validade em formato CSV."""
    dados = obter_relatorio_perdas()
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)

    # Cabeçalho
    writer.writerow([
        'ID Movimentação', 'Data / Hora Descarte', 'Produto', 'Código de Barras',
        'Categoria', 'Lote', 'Data Validade', 'Fornecedor', 'Quantidade Descartada',
        'Unidade', 'Custo Unitário (R$)', 'Prejuízo Total (R$)', 'Motivo', 'Responsável'
    ])

    for i in dados['itens']:
        writer.writerow([
            i['id'],
            i['data_hora'],
            i['produto_nome'],
            i['codigo_barras'] or 'S/N',
            i['categoria'],
            i['numero_lote'] or 'Geral',
            i['data_validade'] or '-',
            i['fornecedor'] or '-',
            i['quantidade'],
            i['unidade_medida'],
            f"{i['preco_custo']:.2f}".replace('.', ','),
            f"{i['prejuizo_financeiro']:.2f}".replace('.', ','),
            i['motivo'],
            i['usuario_nome']
        ])

    hoje = date.today().isoformat()
    nome_arquivo = f"relatorio_perdas_vencimento_{hoje}.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={nome_arquivo}"}
    )

@main_bp.route('/relatorios/exportar/compras')
@login_required
def exportar_compras_csv():
    """Gera download da lista de compras e reposição em formato CSV."""
    dados = obter_relatorio_compras()
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)

    # Cabeçalho
    writer.writerow([
        'ID Produto', 'Produto', 'Código de Barras', 'Categoria', 'Unidade',
        'Saldo Atual', 'Estoque Mínimo', 'Déficit Atual', 'Sugestão de Pedido',
        'Custo Unitário (R$)', 'Custo Total Estimado (R$)', 'Fornecedor Sugerido'
    ])

    for i in dados['itens']:
        writer.writerow([
            i['produto_id'],
            i['nome'],
            i['codigo_barras'],
            i['categoria'],
            i['unidade'],
            i['saldo_atual'],
            i['estoque_minimo'],
            i['deficit'],
            i['sugestao_compra'],
            f"{i['preco_custo']:.2f}".replace('.', ','),
            f"{i['custo_total_previsto']:.2f}".replace('.', ','),
            i['fornecedor_sugerido']
        ])

    hoje = date.today().isoformat()
    nome_arquivo = f"pedido_compras_reposicao_{hoje}.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={nome_arquivo}"}
    )
