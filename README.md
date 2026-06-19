# Market Price Tracker 🛒📈

Este é um projeto desenvolvido no estilo **Homelab** para acompanhar preços de supermercado, ajudando a monitorar a inflação pessoal e identificar casos de *reduflação* (shrinkflation).

O projeto é construído usando **FastAPI**, **SQLite**, **SQLAlchemy 2.0+**, templates **Jinja2**, **Tailwind CSS (via CDN)** e **Chart.js (via CDN)**.

---

## 🚀 Como Iniciar o Projeto do Zero

Siga os passos abaixo para preparar o ambiente e rodar o servidor em sua máquina Windows.

### Passo 1: Criar um Ambiente Virtual (Venv)
No terminal (PowerShell ou CMD), dentro da pasta do projeto, crie um ambiente virtual Python para isolar as dependências:

```powershell
python -m venv venv
```

### Passo 2: Ativar o Ambiente Virtual
Ative o ambiente virtual para que os pacotes sejam instalados nele:

* **No PowerShell:**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
  *(Se receber um erro de permissão de execução, você pode rodar `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` e tentar novamente)*

* **No CMD:**
  ```cmd
  .\venv\Scripts\activate.bat
  ```

### Passo 3: Instalar as Dependências
Com o ambiente virtual ativo, instale as dependências listadas no arquivo `requirements.txt`:

```powershell
pip install -r requirements.txt
```

### Passo 4: Configurar o Arquivo `.env`
O arquivo `.env` já vem pré-configurado na raiz do projeto com as seguintes variáveis:
```env
DATABASE_URL=sqlite:///./data/precos.db
ADMIN_USER=admin
ADMIN_PASSWORD=homelab_admin_123
SECRET_KEY=qJ_dtU4wuX6Ev51ICwGiXrF2sFz2rlQrMBb_6lsiWdg
```
Você pode alterar o usuário e a senha administrativa conforme desejar.

### Passo 5: Iniciar o Servidor de Desenvolvimento
Inicie o servidor uvicorn com recarregamento automático (auto-reload):

```powershell
uvicorn app.main:app --reload
```

Pronto! Agora você pode acessar o projeto nos seguintes links:
* **Painel Principal (Dashboard):** [http://localhost:8000/](http://localhost:8000/)
* **Painel Administrativo Seguro (SQLAdmin):** [http://localhost:8000/admin](http://localhost:8000/admin) (Use o usuário e senha definidos no `.env`)
* **Inspeção de Esquema do Banco de Dados:** [http://localhost:8000/admin/schema](http://localhost:8000/admin/schema) (Acessível de forma segura dentro do painel administrativo)

---

## 📁 Estrutura do Projeto

* `app/`
  * `main.py` - Ponto de entrada da aplicação, configuração do FastAPI e SQLAdmin.
  * `database.py` - Conexão com o banco de dados SQLite.
  * `models.py` - Modelos de tabelas do SQLAlchemy.
  * `schemas.py` - Schemas do Pydantic para validação.
  * `admin.py` - Configuração e segurança do painel administrativo SQLAdmin.
  * `routes/` - Rotas da API e da Web (Jinja2).
  * `templates/` - Páginas HTML estilizadas com Tailwind CSS.
  * `static/` - Arquivos estáticos (JavaScript customizado, etc.).
* `data/` - Pasta onde o banco de dados `precos.db` é criado.
* `.env` - Arquivo de variáveis de ambiente.
* `requirements.txt` - Lista de dependências.
