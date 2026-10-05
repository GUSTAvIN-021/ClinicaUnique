# Publicar o Unique no Render

Este guia publica duas partes do sistema:

- **unique-web**: a interface que a clínica abre no navegador;
- **unique-api**: o backend, que aplica as regras de acesso;
- **unique-postgres**: o banco de dados gerenciado.

O arquivo `render.yaml` descreve essa estrutura sem incluir senhas ou dados de pacientes.

## Custo inicial estimado

Para colocar a primeira versão em uso, a configuração começa no menor plano pago
sempre ativo:

- interface estática: sem custo de computação;
- API: aproximadamente US$ 7/mês;
- PostgreSQL gerenciado: aproximadamente US$ 6/mês;
- total estimado: aproximadamente **US$ 13/mês**, antes de consumo excedente de
  banda ou armazenamento.

Essa é uma configuração inicial. Se a clínica crescer ou a agenda ficar lenta,
o banco e a API podem ser aumentados pelo painel, sem perder os dados.

## Antes de começar

1. Confirme que o código atual está no GitHub.
2. Guarde o backup local criado após a migração: `backups/unique-after-legacy-import.sql`.
3. Crie uma conta no [Render](https://render.com/) com o mesmo GitHub onde está o repositório.

Não envie a pasta `imports`, a pasta `backups` nem o arquivo `backend/.env` ao GitHub.

## Criar a infraestrutura

1. No Render, use **New +** > **Blueprint**.
2. Conecte o repositório `GUSTAvIN-021/ClinicaUnique` e confirme a leitura de `render.yaml`.
3. Escolha uma região próxima da clínica e crie os recursos.
4. Quando o Render mostrar a URL do serviço **unique-api**, abra suas variáveis e defina:

   - `CORS_ORIGINS`: a URL HTTPS do serviço **unique-web**;
   - `SEED_ADMIN_PASSWORD`: uma senha forte e exclusiva para o administrador inicial.

5. No serviço **unique-web**, defina `VITE_API_URL` como a URL da API seguida de `/api`. Exemplo:

   ```text
   https://unique-api.onrender.com/api
   ```

6. Clique em **Manual Deploy** no `unique-web` depois de definir `VITE_API_URL`. Isso faz a interface ser compilada com o endereço correto da API.

## Levar os dados atuais

O banco novo do Render começa vazio. Depois de a API estar no ar, restaure o backup local usando as instruções de conexão externa do banco no painel do Render. Faça isso somente uma vez e mantenha o backup local guardado.

Antes da restauração, eu vou validar com você a URL de conexão fornecida pelo Render e passar o comando exato. A URL contém senha do banco, portanto não a envie pelo GitHub nem a publique em capturas de tela.

## Domínio e segurança

Depois da validação, conecte um domínio próprio à interface, como `sistema.suaclinica.com.br`. O Render gera HTTPS automaticamente. Para o uso da clínica, mantenha o banco gerenciado, configure backups e nunca use um plano que suspenda o serviço por inatividade.

## Conferência final

1. Abra a URL da interface em uma janela anônima.
2. Entre com o administrador.
3. Confira pacientes, agenda e prontuários importados.
4. Faça um teste de acesso com profissional e confirme que ele não enxerga pacientes sem vínculo.
5. Confirme que o logout funciona.
