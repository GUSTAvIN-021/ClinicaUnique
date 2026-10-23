# Backup e restauração — Unique

Os dados de saúde são dados pessoais sensíveis. O backup precisa ser tratado como
um registro clínico: com acesso mínimo, cópia protegida e teste de recuperação.

## Rotina mínima recomendada

1. No Render, confirme no serviço PostgreSQL qual é a política de backups e a
   retenção do plano contratado. A clínica deve ter pelo menos uma cópia diária
   automatizada e uma retenção que tenha sido aprovada pela administração.
2. Faça uma cópia externa criptografada, em local separado da conta do Render,
   pelo menos semanalmente. Não use pendrive compartilhado e nunca envie o
   arquivo por WhatsApp ou e-mail comum.
3. Restrinja o acesso ao local dos backups apenas à direção e a uma pessoa
   técnica nomeada. Guarde quem possui esse acesso.
4. Teste a restauração em um banco de testes a cada trimestre. Um backup que
   nunca foi restaurado ainda não foi comprovado.
5. Mantenha um registro simples: data, responsável, resultado e qualquer falha.

## Exportar uma cópia manual

Use uma máquina confiável. A URL do banco é sigilosa: cole-a somente no prompt
protegido e não a salve em arquivos, no histórico de comandos ou no Git.

```powershell
$secureUrl = Read-Host "Cole a External Database URL do Render" -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureUrl)
$env:UNIQUE_BACKUP_DATABASE_URL = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)

$stamp = Get-Date -Format "yyyy-MM-dd_HHmm"
docker run --rm -e DATABASE_URL="$env:UNIQUE_BACKUP_DATABASE_URL" postgres:16-alpine `
  sh -c 'pg_dump "$DATABASE_URL" --format=custom --no-owner --no-acl' `
  | Set-Content -Encoding Byte "unique_$stamp.backup"

Remove-Item Env:\UNIQUE_BACKUP_DATABASE_URL
```

Depois, mova o arquivo para o cofre/armazenamento criptografado definido pela
clínica e apague a cópia local quando ela não for mais necessária.

## Restaurar

**Nunca restaure diretamente no banco em produção sem autorização explícita da
direção e sem uma cópia atual do estado existente.** Primeiro restaure em um
banco de testes, valide pacientes, prontuários e agenda e só então planeje uma
janela de manutenção para a produção.

Antes de qualquer restauração em produção, registre: quem autorizou, qual backup
será usado, data/hora e o plano de retorno.

## Incidentes e acessos

- Troque imediatamente as credenciais do banco se uma URL ou senha tiver sido
  exposta em chat, print, repositório ou computador não confiável.
- Desative usuários que deixarem a equipe no mesmo dia.
- Preserve a trilha de auditoria; não inclua conteúdo de prontuários nela.
- Em caso de possível vazamento, comunique a direção e avalie com a assessoria
  jurídica a necessidade de notificação à ANPD e aos titulares.
