# Unique

Sistema de gestão para clínicas multidisciplinares, com FastAPI/PostgreSQL no backend e React/TypeScript no frontend. A base foi desenhada para separar API e interface e facilitar futura evolução para o SaaS Vittae.

## Arquitetura e segurança

- JWT enviado exclusivamente em cookie `HttpOnly`; o frontend usa `credentials: include` e não grava tokens em `localStorage`.
- Cookie CSRF separado, comparado ao cabeçalho `X-CSRF-Token` nas mutações.
- Senhas com Argon2 (`pwdlib`); nenhum segredo ou senha inicial existe no código.
- Autorização no backend: profissionais somente enxergam pacientes vinculados e registros do próprio escopo. O serviço de acesso é aplicado antes de carregar recursos por ID.
- Agenda valida disponibilidade e colisões no backend. Um intervalo que começa às 12:00 é válido quando estiver totalmente contido em uma disponibilidade configurada.

## Execução local

1. Copie `backend/.env.example` para `backend/.env`; defina um `JWT_SECRET` longo e `SEED_ADMIN_PASSWORD`.
2. Inicie a aplicação inteira: `docker compose up --build`. O Compose aplica a migration inicial e cria o administrador apenas quando `SEED_ADMIN_PASSWORD` estiver definido.
3. Abra `http://localhost:5173`; a documentação da API estará em `http://localhost:8000/docs`.
4. Para desenvolvimento sem containers: inicie o PostgreSQL, em `backend` crie um ambiente virtual, instale `pip install -r requirements.txt`, execute `alembic upgrade head`, `python -m app.seed` e `uvicorn app.main:app --reload`. Em outro terminal, execute `npm install` e `npm run dev` em `frontend`.

Também é possível usar `docker compose up --build` depois de preparar `backend/.env` com a URL de banco adequada ao serviço `db`.

## Migrations e testes

As migrations devem ser sempre criadas por Alembic e revisadas antes do merge. Os testes de integração precisam rodar contra uma base isolada e cobrir login, RBAC, vínculo profissional–paciente, bloqueio de conflito e disponibilidade às 12:00.
