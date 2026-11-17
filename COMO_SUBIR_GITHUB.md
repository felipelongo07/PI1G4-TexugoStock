# 🐙 Guia: Como Subir o Projeto TexugoStock para o GitHub

Este guia explica o passo a passo direto para você enviar o **TexugoStock Enterprise** para o seu repositório no **GitHub**, permitindo que o professor clone e realize o deploy diretamente no servidor e domínio disponíveis.

---

## 📋 Passo 1: Criar o Repositório no GitHub

1. Acesse sua conta no [GitHub](https://github.com/);
2. No canto superior direito, clique em **"+"** -> **"New repository"**;
3. Preencha os campos:
   - **Repository name**: `TexugoStock` (ou o nome que preferir);
   - **Public**: Deixe como Público para facilitar o clone pelo professor no servidor;
   - **IMPORTANTE**: **NÃO marque** as opções *"Add a README file"*, *".gitignore"* ou *"Choose a license"*, pois o projeto já possui todos esses arquivos pré-configurados!
4. Clique em **"Create repository"**;
5. Copie a URL HTTPS gerada (exemplo: `https://github.com/SEU_USUARIO/TexugoStock.git`).

---

## 💻 Passo 2: Enviar os Arquivos pelo Terminal / PowerShell

Abra o **PowerShell** ou **Prompt de Comando (CMD)** dentro da pasta do projeto (`c:\Users\User\Desktop\projeto github`) e execute:

```bash
# 1. Inicializa o repositório Git local
git init

# 2. Adiciona todos os arquivos do projeto
git add .

# 3. Cria o commit de entrega com todo o sistema pronto
git commit -m "feat: TexugoStock Enterprise - Sistema de Gestao de Estoque e Validade (Producao)"

# 4. Define a branch principal como main
git branch -M main

# 5. Adiciona o endereço do seu repositório no GitHub (substitua com o link copiado no Passo 1)
git remote add origin https://github.com/SEU_USUARIO/TexugoStock.git

# 6. Envia todo o projeto para o GitHub
git push -u origin main
```

> **Nota se você já havia inicializado o Git antes:**
> Caso o repositório já tenha sido iniciado, basta executar:
> ```bash
> git add .
> git commit -m "feat: Preparacao completa para deploy em producao no dominio"
> git push origin main
> ```

---

## 🖥️ Alternativa: Enviando pelo Visual Studio Code

Se você preferir usar a interface gráfica do **VS Code**:
1. Abra a pasta do projeto no VS Code;
2. Clique no ícone de **Controle de Versão** (barra lateral esquerda, ou `Ctrl + Shift + G`);
3. Digite a mensagem do commit: `feat: TexugoStock Enterprise Pronto para Producao`;
4. Clique no botão **Commit** (ícone de ✔️);
5. Clique em **"Publish Branch"** ou **"Sync Changes"**;
6. Selecione a sua conta do GitHub e confirme o envio.

---

## 🚀 Como o Professor fará a Hospedagem no Domínio

Assim que o projeto estiver no GitHub, o professor só precisará acessar o repositório. O projeto já inclui o guia técnico completo de infraestrutura em:
📄 **[HOSPEDAGEM_E_DEPLOY.md](HOSPEDAGEM_E_DEPLOY.md)**

O professor poderá escolher entre:
- **Docker Compose (1 comando)**: `docker compose up -d`
- **Linux VPS + Nginx + Gunicorn (Systemd com SSL Let's Encrypt no domínio)**
- **cPanel / Cloud (Render, Railway, PythonAnywhere)**
- **Servidor Interno com Waitress WSGI**: `python server_production.py`
