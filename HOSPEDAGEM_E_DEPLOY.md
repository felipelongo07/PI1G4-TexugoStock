# 🚀 Guia Técnico de Hospedagem & Deploy — TexugoStock Enterprise

> **Manual de Implantação para o Administrador de Infraestrutura / Professor**  
> Instruções completas para publicação da aplicação web em servidores Linux, Docker, cPanel ou Cloud com apontamento de domínio próprio e certificado SSL (HTTPS).

---

## 📌 1. Visão Geral da Arquitetura

- **Framework**: Python 3.10+ / Flask 3.0+
- **Padrão WSGI**: `wsgi.py` (expõe o callable `app = create_app()`)
- **Suporte a Proxy Reverso**: Configurado nativamente com `ProxyFix` (preserva cabeçalhos `X-Forwarded-Proto`, `X-Forwarded-Host` e garante redirecionamentos HTTPS perfeitos)
- **Banco de Dados**: SQLite3 Relacional (autocontido em `texugostock.db` ou caminho configurável por variável de ambiente)
- **Porta Padrão**: `5000` (ou customizável via variável de ambiente `$PORT`)
- **Servidores WSGI Homologados**: Gunicorn (Linux/Docker) ou Waitress (Windows/Linux)

### 🔑 Credenciais Padrão do Administrador:
- **E-mail**: `admin@texugostock.com`
- **Senha Inicial**: `admin123`
*(As tabelas e o usuário administrador são criados automaticamente caso o banco não exista).*

---

## ⚙️ 2. Variáveis de Ambiente Suportadas

Opcionalmente, o servidor pode definir as variáveis abaixo (via `.env`, Systemd, Docker ou painel da nuvem):

| Variável | Padrão | Descrição |
| :--- | :--- | :--- |
| `PORT` | `5000` | Porta TCP na qual o servidor web escutará |
| `SECRET_KEY` | *(chave aleatória segura)* | Chave de criptografia de sessões corporativas |
| `DATABASE_PATH` | `./texugostock.db` | Caminho absoluto ou relativo do arquivo do banco SQLite |
| `WAITRESS_THREADS` | `6` | Quantidade de threads simultâneas para o servidor Waitress |

---

## 🐧 3. Método 1: Deploy em Servidor Linux VPS (Ubuntu / Debian + Nginx + Gunicorn)

Este é o método tradicional mais utilizado para apontamento de domínio com **Nginx** e certificado **SSL Let's Encrypt (HTTPS gratuito)**.

### Passo 1: Clonar o projeto e criar o ambiente virtual
```bash
# 1. Clone o repositório para o diretório do servidor (ex: /var/www/)
cd /var/www
git clone https://github.com/SEU_USUARIO/TexugoStock.git texugostock
cd texugostock

# 2. Crie e ative o ambiente virtual Python
python3 -m venv venv
source venv/bin/activate

# 3. Instale as dependências
pip install --upgrade pip
pip install -r requirements.txt gunicorn

# 4. Inicialize o banco de dados e os dados iniciais
python seed_data.py
```

---

### Passo 2: Criar o Serviço Systemd (Gunicorn em Segundo Plano)
Crie o arquivo de serviço para que a aplicação inicie automaticamente com o sistema:
```bash
sudo nano /etc/systemd/system/texugostock.service
```

Cole o conteúdo abaixo (ajuste o usuário `www-data` ou seu usuário Linux):
```ini
[Unit]
Description=Servico Gunicorn para TexugoStock Enterprise
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/texugostock
Environment="PATH=/var/www/texugostock/venv/bin"
Environment="PORT=5000"
ExecStart=/var/www/texugostock/venv/bin/gunicorn --workers 3 --threads 2 --bind 127.0.0.1:5000 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Ative e inicie o serviço:
```bash
# Permissão para o usuário www-data ler e gravar o banco SQLite
sudo chown -R www-data:www-data /var/www/texugostock

# Inicia o serviço
sudo systemctl daemon-reload
sudo systemctl start texugostock
sudo systemctl enable texugostock

# Verifica se está rodando
sudo systemctl status texugostock
```

---

### Passo 3: Configurar o Nginx como Proxy Reverso para o Domínio
Crie a configuração do site no Nginx:
```bash
sudo nano /etc/nginx/sites-available/texugostock
```

Adicione a configuração (substitua `seu-dominio.com.br` pelo domínio real):
```nginx
server {
    listen 80;
    server_name seu-dominio.com.br www.seu-dominio.com.br;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # Arquivos estáticos servidos diretamente com cache pelo Nginx (alta performance)
    location /static/ {
        alias /var/www/texugostock/app/static/;
        expires 30d;
    }
}
```

Ative o site e reinicie o Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/texugostock /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

### Passo 4: Instalar Certificado SSL Gratuito (HTTPS com Certbot)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d seu-dominio.com.br -d www.seu-dominio.com.br
```
O Certbot configurará o redirecionamento automático de HTTP para HTTPS no domínio. O sistema estará acessível e seguro via `https://seu-dominio.com.br`!

---

## 🐳 4. Método 2: Deploy com Docker & Docker Compose (Recomendado)

O projeto já contém `Dockerfile` e `docker-compose.yml` prontos para produção.

### Passo 1: Subir o Container
Na pasta do projeto, execute:
```bash
docker compose up -d --build
```

O container compilará o ambiente, inicializará as tabelas SQLite e executará o **Gunicorn** na porta `5000`.

### Passo 2: Apontamento no Nginx / Nginx Proxy Manager / Traefik
Basta configurar uma regra de proxy reverso encaminhando o tráfego do seu domínio para:
`http://IP_DO_SERVIDOR:5000` (ou para `http://texugostock_app:5000` dentro da rede Docker).

---

## 🌐 5. Método 3: Hospedagem Compartilhada / cPanel (Setup Python App)

Se o professor utiliza hospedagem baseada em **cPanel com CloudLinux (Passenger)**:

1. Suba os arquivos do projeto para o diretório da conta (ex: `~/texugostock/`);
2. No cPanel, abra a ferramenta **"Setup Python App"**;
3. Clique em **"Create Application"**:
   - **Python version**: Selecione 3.10, 3.11 ou 3.12;
   - **Application root**: `texugostock`;
   - **Application URL**: Selecione o domínio ou subdomínio desejado;
   - **Application startup file**: `wsgi.py`;
   - **Application Entry point**: `app`;
4. Clique em **Create**;
5. Acesse o terminal SSH do cPanel ou clique em **"Run Pip Install"** apontando para o `requirements.txt`;
6. Clique em **"Restart Application"**.

---

## ☁️ 6. Método 4: Deploy em Plataformas de Nuvem (Render, Railway, Fly.io)

O repositório já conta com o arquivo [Procfile](file:///c:/Users/User/Desktop/projeto%20github/Procfile) (`web: gunicorn wsgi:app`).

- **No Render (render.com)**:
  1. Crie uma nova **Web Service** e conecte seu repositório do GitHub;
  2. Defina o **Environment**: `Python 3`;
  3. **Build Command**: `pip install -r requirements.txt && python seed_data.py`;
  4. **Start Command**: `gunicorn wsgi:app`;
  5. Adicione um disco persistente (Disk) caso deseje manter o arquivo `.db` permanentemente entre reinicializações.

- **No Railway (railway.app)**:
  1. Clique em **"New Project"** -> **"Deploy from GitHub repo"**;
  2. O Railway detectará o `Procfile` e `requirements.txt` automaticamente e subirá a aplicação com URL pública HTTPS.

---

## 💾 7. Rotina de Backup do Banco de Dados

Como o banco é o SQLite relacional em arquivo único (`texugostock.db`):
- O backup consiste simplesmente em copiar o arquivo `texugostock.db`.
- Para automatizar backup diário via Cron no Linux:
  ```bash
  0 3 * * * cp /var/www/texugostock/texugostock.db /backups/texugostock_$(date +\%Y\%m\%d).db
  ```

---

## 🩺 8. Teste de Funcionamento / Healthcheck

Após o deploy, teste no terminal do servidor:
```bash
curl -I http://127.0.0.1:5000/login
```
Resposta esperada: `HTTP/1.1 200 OK`.

