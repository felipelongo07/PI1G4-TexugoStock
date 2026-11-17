import os
from flask import Flask
from app.database import init_db

def create_app():
    """Fábrica da aplicação Flask para o TexugoStock."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'texugostock-enterprise-production-key-99827401')

    # Inicializa o banco de dados SQLite caso ainda não exista
    with app.app_context():
        init_db()

    # Filtros Jinja personalizados para datas e valores em Real (R$)
    @app.template_filter('moeda')
    def formato_moeda(valor):
        try:
            return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        except (ValueError, TypeError):
            return "R$ 0,00"

    @app.template_filter('data_br')
    def formato_data_br(data_str):
        if not data_str:
            return '-'
        try:
            partes = str(data_str)[:10].split('-')
            if len(partes) == 3:
                return f"{partes[2]}/{partes[1]}/{partes[0]}"
            return data_str
        except Exception:
            return data_str

    # Processador de contexto para injetar dados da empresa e variáveis globais nos templates
    @app.context_processor
    def injetar_globais():
        from flask import session
        from app.models import obter_configuracao
        return {
            'NOME_APP': 'TexugoStock Enterprise',
            'SUBTITULO_APP': 'Gestão Profissional de Estoque & Validade',
            'EMPRESA_NOME': obter_configuracao('empresa_nome', 'Texugo Distribuição Ltda.'),
            'EMPRESA_CNPJ': obter_configuracao('empresa_cnpj', '12.345.678/0001-90'),
            'EMPRESA_TELEFONE': obter_configuracao('empresa_telefone', '(11) 3456-7890'),
            'EMPRESA_EMAIL': obter_configuracao('empresa_email', 'contato@texugostock.com'),
            'EMPRESA_ENDERECO': obter_configuracao('empresa_endereco', 'Av. Empresarial, 1000 - Centro'),
            'usuario_logado': session.get('usuario')
        }

    # Registro das rotas principais
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # Suporte a Proxy Reverso (Nginx, Apache, Cloudflare, Traefik) para domínios e HTTPS
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    return app

