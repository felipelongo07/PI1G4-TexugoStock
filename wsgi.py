"""
TexugoStock Enterprise - Ponto de Entrada WSGI de Produção
Compatível com Gunicorn, uWSGI, Nginx, Apache mod_wsgi, cPanel Passenger, Docker e Cloud PaaS.
"""
import os
from app import create_app
from app.database import init_db

# Garante que o banco de dados e as tabelas estejam criados na primeira execução
init_db()

# Cria a instância padrão da aplicação WSGI
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

