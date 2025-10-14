# Mapeamento API ↔ Excel para certificação de clientes

A certificação de clientes lê o ficheiro Excel fornecido pelo utilizador, identifica as colunas através dos sinónimos suportados e atualiza alguns campos com base na resposta da API pública da AGT (`/commonServer/common/taxpayer/get/{nif}`).

## Colunas canónicas do Excel

As colunas do Excel são normalizadas para uma forma canónica antes de qualquer processamento. A tabela seguinte resume as colunas necessárias e os nomes alternativos reconhecidos:

| Coluna canónica | Sinónimos reconhecidos |
| ---------------- | ---------------------- |
| `Codigo` | `codigo`, `cod`, `cod_cliente`, `codigo_cliente`, `codigo_de_cliente`, `client_code` |
| `NIF` | `nif`, `nif_cliente`, `contribuinte`, `numero_contribuinte`, `num_contribuinte`, `n_contribuinte`, `no_contribuinte`, `nro_contribuinte`, `num_contrib`, `numero_nif`, `nif_numero` |
| `Nome` | `nome`, `nome_cliente`, `cliente`, `designacao`, `designacao_social`, `razao_social` |
| `Morada` | `morada`, `endereco`, `endereco_cliente`, `endereco_postal`, `endereco_fiscal`, `address` |
| `Localidade` | `localidade`, `cidade`, `municipio`, `localizacao`, `local`, `cidade_cliente`, `city` |

Estas colunas são obrigatórias. Caso falte alguma, o processamento termina com erro.
O campo `Codigo` no ficheiro excel corressponde à Primary Key (PK) na base de dados do cliente.

## Dados recebidos da API

A API devolve, quando existe um registo válido, um objecto com os campos:

- `companyName`
- `gsmc`
- `nsrdz`
- `hdzt`

## Mapeamento dos campos API → Excel

| Campo da API | Coluna canónica do Excel | Regra aplicada |
| ------------- | ------------------------ | -------------- |
| `nif` | `Contribuinte` | Numero de Identificação Fiscal a Validar. |
| `companyName` | `Nome` | Se existir texto em `companyName`, substitui o conteúdo da coluna `Nome`. |
| `gsmc` | `Nome` | Apenas usado quando `companyName` está vazio; serve como valor alternativo para a coluna `Nome`. |
| `nsrdz` | `Morada` | Quando existe texto em `nsrdz`, sobrepõe a morada no Excel. |
| `hdzt` | `Localidade` | Se `hdzt` não for a string `"ACTIVE"`, a coluna `Localidade` recebe o aviso `"Contribuinte INACTIVO na AGT"`. |

Adicionalmente, a coluna `Localidade` pode receber mensagens de erro independentes da API:

- `"NIF INVALIDO | Manifestamente errado"` quando o NIF viola claramente as regras básicas (tamanho inválido, caracteres impróprios, vazio, etc.);
- `"NIF INVALIDO | Possivelmente errado"` quando o formato parece plausível mas não foi possível confirmar com a API da AGT;
- `"NIF DUPLICADO - {primeiro_codigo}`" para sinalizar NIFs repetidos no ficheiro.

As colunas `Codigo` e `NIF` não são preenchidas pela API; servem para identificar os registos no Excel e para construir as chamadas à API, respectivamente.
