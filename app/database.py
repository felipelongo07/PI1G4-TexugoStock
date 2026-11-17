import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.environ.get('DATABASE_PATH') or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'texugostock.db')

def get_db_connection():
    """Retorna uma conexão configurada com o banco SQLite."""
    # Garante que o diretório do banco de dados exista (essencial para Docker e volumes persistentes)
    db_dir = os.path.dirname(os.path.abspath(DB_PATH))
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Cria e atualiza o esquema do banco de dados relacional."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Tabela de Usuários (RF05, RNF05)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        senha_hash TEXT NOT NULL,
        perfil TEXT NOT NULL CHECK(perfil IN ('admin', 'estoquista')),
        cargo TEXT DEFAULT 'Colaborador',
        ativo INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Tabela de Produtos (RF01, RF04, RF08)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_barras TEXT UNIQUE,
        nome TEXT NOT NULL,
        categoria TEXT NOT NULL,
        unidade_medida TEXT NOT NULL DEFAULT 'UN',
        preco_custo REAL DEFAULT 0.0,
        preco_venda REAL NOT NULL DEFAULT 0.0,
        estoque_minimo INTEGER NOT NULL DEFAULT 5,
        descricao TEXT,
        ativo INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. Tabela de Lotes e Validades (RF02, RF03, RF07)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto_id INTEGER NOT NULL,
        numero_lote TEXT NOT NULL,
        quantidade_inicial INTEGER NOT NULL,
        quantidade_atual INTEGER NOT NULL,
        data_validade DATE NOT NULL,
        fornecedor TEXT,
        data_recebimento DATE DEFAULT (DATE('now')),
        observacoes TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (produto_id) REFERENCES produtos(id) ON DELETE CASCADE
    );
    """)

    # 4. Tabela de Fornecedores Homologados
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fornecedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        razao_social TEXT NOT NULL,
        nome_fantasia TEXT,
        cnpj TEXT UNIQUE,
        telefone TEXT,
        email TEXT,
        contato_responsavel TEXT,
        cidade TEXT,
        uf TEXT,
        observacoes TEXT,
        ativo INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 5. Tabela de Movimentações de Estoque (RF03, RF05, RF06)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS movimentacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto_id INTEGER NOT NULL,
        lote_id INTEGER,
        tipo TEXT NOT NULL CHECK(tipo IN ('ENTRADA', 'SAIDA_VENDA', 'AJUSTE', 'DESCARTE_VENCIDO')),
        quantidade INTEGER NOT NULL,
        usuario_id INTEGER,
        motivo TEXT,
        data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (produto_id) REFERENCES produtos(id),
        FOREIGN KEY (lote_id) REFERENCES lotes(id),
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    );
    """)

    # 6. Tabela de Parâmetros e Configurações Gerais
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configuracoes (
        chave TEXT PRIMARY KEY,
        valor TEXT NOT NULL
    );
    """)

    # Configurações padrão corporativas
    cursor.execute("INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES ('dias_alerta_validade', '15')")
    cursor.execute("INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES ('nome_sistema', 'TexugoStock Enterprise')")
    cursor.execute("INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES ('empresa_nome', 'Texugo Comércio & Distribuição Ltda.')")
    cursor.execute("INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES ('empresa_cnpj', '12.345.678/0001-90')")
    cursor.execute("INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES ('empresa_telefone', '(11) 3456-7890')")
    cursor.execute("INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES ('empresa_email', 'contato@texugostock.com')")
    cursor.execute("INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES ('empresa_endereco', 'Av. Empresarial, 1000 - Centro')")

    # Criação do usuário administrador padrão caso ainda não exista nenhum
    cursor.execute("SELECT COUNT(*) AS total FROM usuarios")
    if cursor.fetchone()['total'] == 0:
        admin_pass = generate_password_hash('admin123')
        estoq_pass = generate_password_hash('estoque123')
        cursor.execute("""
        INSERT INTO usuarios (nome, email, senha_hash, perfil, cargo)
        VALUES ('Administrador Gestor', 'admin@texugostock.com', ?, 'admin', 'Gerente Geral')
        """, (admin_pass,))
        cursor.execute("""
        INSERT INTO usuarios (nome, email, senha_hash, perfil, cargo)
        VALUES ('Felipe Estoquista', 'estoque@texugostock.com', ?, 'estoquista', 'Responsável pelo Estoque')
        """, (estoq_pass,))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Banco de dados TexugoStock inicializado com sucesso!")

