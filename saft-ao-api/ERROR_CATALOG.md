# Catálogo de Erros e Avisos

| code | http | tipo | mensagem | acção |
|------|------|------|----------|-------|
| INVALID_CREDENTIALS | 401 | ERROR | Utilizador/senha inválidos | Rever credenciais |
| FILE_MISSING | 400 | ERROR | Campo `file` ausente | Reenviar com ficheiro |
| FILE_TOO_LARGE | 413 | ERROR | Ficheiro excede limite | Dividir período |
| INVALID_XML | 400 | ERROR | XML mal formado | Corrigir fonte |
| XSD_VALIDATION_FAILED | 422 | ERROR | Falha no XSD | Ver `details[]` |
| BUSINESS_RULE_FAILED | 422 | ERROR | Regra de negócio reprovada | Corrigir dados |
| AUTO_FIX_NOT_POSSIBLE | 409 | WARNING | Fix inseguro | Corrigir manualmente |
| NOT_FOUND | 404 | ERROR | Recurso inexistente | Ver ID |
