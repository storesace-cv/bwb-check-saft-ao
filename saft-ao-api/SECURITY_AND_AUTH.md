# Segurança e Autenticação

## Autenticação
- **JWT** com expiração curta (p.ex. 1h) e refresh tokens (opcional).
- `Authorization: Bearer <token>` em todas as rotas (excepto `/auth/login`).

## Autorização
- Perfis: `admin`, `partner`, `operator`.
- Escopos mínimos por rota (least-privilege).

## Protecção de Dados
- Criptografia **em trânsito** (TLS 1.2+).
- Criptografia **em repouso** (chaves geridas no KMS).
- Pseudonimização em ambientes de teste.
- Logs sem dados sensíveis (ou mascarados).

## Auditoria
- Trilha completa: quem enviou, quando, IP, hash SHA‑256 do ficheiro, versões geradas, downloads e submissões.
