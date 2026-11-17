# Imagem base oficial Python leve
FROM python:3.12-slim

# Evita criação de arquivos .pyc e faz flush imediato de logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# Diretório de trabalho no container
WORKDIR /app

# Instala curl para healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Instala dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copia todo o código da aplicação
COPY . .

# Inicializa o banco de dados e semeia os dados corporativos iniciais
RUN python -c "from app.database import init_db; init_db()" && python seed_data.py

# Porta padrão exposta
EXPOSE 5000

# Comando padrão de inicialização com Gunicorn (3 workers, multi-thread)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "--threads", "2", "wsgi:app"]

