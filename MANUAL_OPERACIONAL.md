# 📘 Manual Operacional do Usuário — TexugoStock Enterprise

> **Guia Oficial de Treinamento e Operação para Colaboradores e Gestores**  
> Versão 1.0.0 Corporativa — Controle Inteligente de Estoque, Lotes e Validades

---

## 📑 Sumário

1. [Visão Geral e Objetivos do Sistema](#1-visão-geral-e-objetivos-do-sistema)
2. [Primeiro Acesso e Login](#2-primeiro-acesso-e-login)
3. [Painel Executivo (Dashboard)](#3-painel-executivo-dashboard)
4. [Configuração dos Dados da Empresa](#4-configuração-dos-dados-da-empresa)
5. [Gestão de Fornecedores Homologados](#5-gestão-de-fornecedores-homologados)
6. [Cadastro e Gestão de Produtos](#6-cadastro-e-gestão-de-produtos)
7. [Rotina de Recebimento de Mercadorias e Lotes](#7-rotina-de-recebimento-de-mercadorias-e-lotes)
8. [Rotina de Vendas e Baixas (Algoritmo FEFO)](#8-rotina-de-vendas-e-baixas-algoritmo-fefo)
9. [Controle Preventivo de Validade e Descarte](#9-controle-preventivo-de-validadade-e-descarte)
10. [Reposição de Estoque e Compras](#10-reposição-de-estoque-e-compras)
11. [Central de Relatórios e Exportação para Excel](#11-central-de-relatórios-e-exportação-para-excel)
12. [Gestão de Usuários e Controle de Acesso (RBAC)](#12-gestão-de-usuários-e-controle-de-acesso-rbac)
13. [Boas Práticas e Recomendações de Segurança](#13-boas-práticas-e-recomendações-de-segurança)

---

## 1. Visão Geral e Objetivos do Sistema

O **TexugoStock Enterprise** foi desenvolvido sob medida para estabelecimentos comerciais (mercados, adegas, empórios, distribuidoras e depósitos) com um propósito central: **eliminar o prejuízo financeiro causado por produtos vencidos na prateleira e evitar a perda de vendas por falta de mercadoria.**

### Diferenciais Operacionais:
- **Algoritmo FEFO (*First Expired, First Out*)**: Sempre que uma venda ou saída for lançada, o sistema dá baixa automática nas unidades do lote que tem a validade mais próxima de vencer, poupando os lotes mais novos;
- **Alerta Visual de Validade em 3 Níveis**:
  - 🟢 **OK (Normal)**: Validade com prazo seguro;
  - 🟡 **Próximo de Vencer**: Produtos que atingiram a janela de atenção configurada (ex: 30 dias);
  - 🔴 **Vencido**: Produtos que atingiram ou passaram da data de expiração, bloqueados para venda comum;
- **Exportação Nativa para Excel**: Todos os dados podem ser exportados em CSV formatado com caracteres brasileiros (`BOM UTF-8`) e delimitador padrão (`;`).

---

## 2. Primeiro Acesso e Login

1. Abra qualquer navegador (Google Chrome, Microsoft Edge, Firefox, Safari) e digite o endereço do servidor:
   - Na máquina servidora: `http://127.0.0.1:5000`
   - Em computadores da rede interna: `http://IP_DO_SERVIDOR:5000`
2. Na tela de login, informe seu e-mail e senha corporativos;
3. Usuários pré-configurados para a implantação:
   - **Administrador**: `admin@texugostock.com` | Senha: `admin123`
   - **Estoquista**: `estoque@texugostock.com` | Senha: `estoque123`
   - **Caixa / Vendas**: `vendas@texugostock.com` | Senha: `vendas123`
4. *Importante*: Após o primeiro acesso, o colaborador deve acessar o menu superior direito **"Meu Perfil"** e definir uma senha individual e confidencial.

---

## 3. Painel Executivo (Dashboard)

A página inicial do sistema consolida a saúde do estoque em tempo real:

- **Métricas Principais**:
  1. *Total de Itens em Estoque*: Saldo físico de todas as unidades ativas;
  2. *Valor em Custo*: Capital imobilizado em mercadorias a preço de custo (R$);
  3. *Valor Potencial de Venda*: Faturamento previsto na venda de todo o estoque (R$);
  4. *Lotes Críticos*: Quantidade de lotes vencidos ou prestes a vencer;
  5. *Itens com Estoque Baixo*: Produtos que estão abaixo da quantidade mínima estipulada;
  6. *Produtos no Catálogo*: Total de mercadorias ativas cadastradas;
- **Painel de Alertas Imediatos**: Apresenta os produtos que exigem ação preventiva imediata da equipe (promoção rápida ou descarte);
- **Histórico Recente**: Relação das últimas movimentações com identificação do colaborador que executou a ação.

---

## 4. Configuração dos Dados da Empresa

*(Exclusivo para o perfil Administrador)*

No menu lateral, acesse **Configurações**:
1. **Dados Cadastrais**: Preencha Razão Social, Nome Fantasia, CNPJ, Telefone Comercial, E-mail de Contato e Endereço Físico. Esses dados serão exibidos no cabeçalho do sistema e nos relatórios gerenciais;
2. **Dias para Alerta de Validade**: Defina com quantos dias de antecedência o sistema deve marcar um lote como "Próximo de Vencer" (exemplo: `30` ou `45` dias);
3. Clique em **"Salvar Configurações"** para aplicar imediatamente em todo o sistema.

---

## 5. Gestão de Fornecedores Homologados

No menu lateral, acesse **Fornecedores**:
1. Para cadastrar um novo fornecedor, clique no botão **"+ Novo Fornecedor"**;
2. Preencha a Razão Social/Nome Fantasia, CNPJ, Telefone, E-mail, Responsável pelo Contato e Cidade/UF;
3. **Status do Fornecedor**:
   - Fornecedores ativos aparecem na lista de seleção rápida durante o recebimento de mercadorias;
   - Caso um fornecedor seja descontinuado, utilize o botão **"Desativar"** para suspender novas compras sem apagar o histórico de lotes já recebidos.

---

## 6. Cadastro e Gestão de Produtos

No menu lateral, acesse **Produtos**:
1. **Cadastrar Produto**: Clique em **"+ Novo Produto"**;
2. Preencha os campos:
   - *Nome do Produto* (ex: "Leite Integral UHT 1L");
   - *Categoria* (ex: "Laticínios", "Bebidas", "Limpeza");
   - *Código de Barras (EAN)*: Pode ser digitado ou lido diretamente com leitor de código de barras USB;
   - *Unidade de Medida* (UN, KG, L, CX, PCT);
   - *Preço de Custo (R$)* e *Preço de Venda (R$)*;
   - *Estoque Mínimo*: Quantidade de segurança para acionar o alerta de reposição;
3. Clique em **"Salvar Produto"**. O sistema direcionará opcionalmente para a tela de lançamento do primeiro lote.

---

## 7. Rotina de Recebimento de Mercadorias e Lotes

Sempre que uma nota fiscal ou entrega física de mercadorias chegar ao estabelecimento:
1. No menu lateral, acesse **Recebimento / Lotes**;
2. Selecione o produto correspondente no catálogo;
3. Informe os dados impressos na embalagem do fabricante:
   - *Número do Lote*: Código alfanumérico impresso pelo fabricante;
   - *Quantidade Recebida*: Número de unidades físicas entregues;
   - *Data de Validade*: Data de expiração impressa na mercadoria;
   - *Fornecedor*: Selecione o fornecedor cadastrado na lista rápida;
   - *Observações / NF*: Número da Nota Fiscal ou detalhes de recebimento;
4. **Triagem Automática**: Se a data digitada já estiver vencida, o sistema emitirá um alerta visual imediato antes da confirmação, impedindo a entrada indevida de mercadorias estragadas;
5. Clique em **"Confirmar Recebimento"**. O saldo do produto é atualizado automaticamente.

---

## 8. Rotina de Vendas e Baixas (Algoritmo FEFO)

Sempre que houver venda no caixa, saída para produção interna ou consumo:
1. No menu lateral, acesse **Saída / Vendas**;
2. Selecione o produto e digite a quantidade vendida/retirada;
3. Informe o motivo (ex: *"Venda Balcão Caixa 01"*, *"Venda PDV"*, *"Transferência"*);
4. Clique em **"Confirmar Saída"**;
5. **Ação Inteligente do Algoritmo FEFO**:
   - O sistema localiza entre todos os lotes em estoque aquele que tem a data de validade mais antiga;
   - Deduz a quantidade exata desse lote prioritário;
   - Se a venda for maior que o saldo do primeiro lote, o sistema consome o primeiro lote por completo e retira o restante do lote seguinte;
   - Se o saldo restante do produto ficar abaixo do estoque mínimo, uma tarja amarela de atenção avisará imediatamente o operador.

---

## 9. Controle Preventivo de Validade e Descarte

No menu lateral, acesse **Controle de Validade**:
1. O painel exibe todos os lotes ativos ordenados pela data de expiração, com contagem regressiva precisa em dias (*"Vence em X dias"* ou *"Vencido há X dias"*);
2. **Filtros Rápidos**: Alterne entre *Todos*, *Apenas Vencidos*, *Próximos do Vencimento* ou *No Prazo*;
3. **Ações Preventivas**:
   - Produtos com 15 a 30 dias de validade restante podem ser colocados em promoção relâmpago no ponto de venda;
4. **Procedimento de Descarte**:
   - Caso um lote atinja a data de validade sem ser vendido, clique no botão vermelho **"Descartar Lote"**;
   - Confirme o motivo do descarte (ex: *"Produto avariado/vencido"*);
   - O saldo físico é zerado imediatamente e o valor de prejuízo financeiro é registrado na contabilidade de perdas da empresa.

---

## 10. Reposição de Estoque e Compras

No menu lateral, acesse **Estoque Baixo**:
1. Essa tela reúne todas as mercadorias cujo saldo atual é menor ou igual ao estoque mínimo de segurança;
2. O sistema calcula automaticamente:
   - *Déficit Atual*: Quantas unidades faltam para alcançar o estoque mínimo;
   - *Sugestão de Compra*: Quantidade ideal de pedido para abastecer a prateleira com folga de segurança;
   - *Custo Total Estimado*: Projeção financeira do investimento necessário;
3. Use o botão **"Imprimir Lista de Pedidos"** para gerar um documento pronto para enviar aos fornecedores ou representantes comerciais.

---

## 11. Central de Relatórios e Exportação para Excel

No menu lateral, acesse **Relatórios**:
O sistema dispõe de 3 relatórios corporativos com download em formato `.csv` compatível com Microsoft Excel, Google Planilhas e LibreOffice Calc:

1. 📊 **Relatório de Inventário Completo**:
   - Relação de todos os produtos, estoques atuais, custo unitário, valor total imobilizado e preços de venda;
2. ⚠️ **Relatório de Perdas por Validade**:
   - Histórico contábil de todas as perdas e descartes efetuados, com data, número de lote, quantidade, motivo e prejuízo financeiro total em Reais (R$);
3. 🛒 **Relatório de Sugestão de Compras e Reposição**:
   - Relação de itens deficitários, fornecedor sugerido, saldo atual, déficit e estimativa de investimento.

> **Dica para o Excel**: Os relatórios já são gerados com assinatura `UTF-8 BOM` e separador ponto-e-vírgula (`;`), o que garante que caracteres com acentos (como ç, ã, é) e valores em Reais abram formatados sem necessidade de conversão manual.

---

## 12. Gestão de Usuários e Controle de Acesso (RBAC)

*(Exclusivo para o perfil Administrador)*

No menu lateral, acesse **Usuários**:
1. **Cadastrar Colaborador**: Clique em **"+ Novo Usuário"** e defina Nome, E-mail corporativo, Perfil de Acesso e Senha Provisória;
2. **Perfis de Acesso**:
   - **Administrador / Gestor**: Acesso irrestrito a configurações, dados financeiros, relatórios, gestão de fornecedores e controle de usuários;
   - **Operador / Estoquista**: Acesso às rotinas diárias operacionais (recebimento, saídas, consulta e auditoria);
3. **Redefinir Senha**: Caso um colaborador esqueça sua senha, o Administrador pode clicar em **"Redefinir Senha"** no card do usuário e cadastrar uma nova credencial;
4. **Bloqueio de Acesso**: Caso um colaborador seja desligado da empresa, clique em **"Desativar"**. O acesso ao sistema é bloqueado imediatamente, mantendo todo o histórico de operações passadas registrado para auditoria.

---

## 13. Boas Práticas e Recomendações de Segurança

1. **Troca Periódica de Senhas**: Cada colaborador deve manter sua senha em sigilo e alterá-la periodicamente no menu "Meu Perfil";
2. **Conferência Física no Recebimento**: Sempre confira o número de lote e a data de validade impressos fisicamente na caixa/rótulo antes de confirmar a entrada no sistema;
3. **Backup do Banco de Dados**:
   - O arquivo do banco de dados encontra-se na pasta `instance/texugostock.db` (ou `texugostock.db` na raiz);
   - Recomenda-se copiar este arquivo periodicamente para um pendrive, HD externo ou serviço de nuvem ao final de cada dia de operação.

