"""
TexugoStock Enterprise - Servidor de Produção (WSGI Waitress)
Pronto para execução contínua (24/7) em ambiente corporativo.
"""
import os
import sys
from waitress import serve
from app import create_app
from app.database import init_db

# Inicializa e garante que o banco de dados e tabelas existam
init_db()

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    threads = int(os.environ.get('WAITRESS_THREADS', 6))

    print("=" * 60)
    print("   TEXUGOSTOCK ENTERPRISE - SERVIDOR DE PRODUÇÃO (WSGI)")
    print("=" * 60)
    print(f" Servidor HTTP : Waitress WSGI Server (Produção 24/7)")
    print(f" Endereço Local : http://127.0.0.1:{port}")
    print(f" Rede Interna   : http://0.0.0.0:{port}")
    print(f" Concorrência   : {threads} threads ativas")
    print("=" * 60)
    print(" Pressione Ctrl+C para encerrar o servidor com segurança.")
    print("-" * 60)

    try:
        serve(app, host='0.0.0.0', port=port, threads=threads)
    except KeyboardInterrupt:
        print("\nServidor finalizado pelo operador.")
        sys.exit(0)

