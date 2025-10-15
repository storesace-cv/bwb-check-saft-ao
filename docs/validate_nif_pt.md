# 📘 Validação Matemática e Estrutural do NIF Português

## 🔎 Objetivo
Descreve o **algoritmo matemático** e as **regras estruturais** usadas para validar um **NIF português**, sem recorrer a base de dados externas.

---

## 🧩 Estrutura
O NIF tem **9 dígitos** (D1–D9). O último dígito é o de controlo.

---

## 🧮 Algoritmo
1. Multiplicar os 8 primeiros dígitos por pesos de 9→2.
2. Calcular `resto = soma mod 11`.
3. Se `resto < 2`, D9 = 0, caso contrário `D9 = 11 - resto`.
4. O NIF é válido se o D9 coincidir com o dígito final.

### Exemplo
NIF: 123456789 → soma=156 → resto=2 → D9=9 → ✅ válido.

---

## 🔢 Prefixos válidos
| Prefixo | Tipo | Observações |
|----------|------|-------------|
| 1–3 | Pessoa singular | Residentes |
| 45 | Pessoa coletiva não residente |  |
| 5 | Empresa / Pessoa coletiva |  |
| 6 | Administração pública |  |
| 8 | Empresário individual |  |
| 9 | Outros / temporários |  |

---

## 💻 Exemplo Python
```python
def nif_valido(nif: str) -> bool:
    if not nif.isdigit() or len(nif) != 9:
        return False
    soma = sum(int(d) * (9 - i) for i, d in enumerate(nif[:8]))
    resto = soma % 11
    digito = 0 if resto < 2 else 11 - resto
    return int(nif[-1]) == digito
```

---

## 🌐 API nif.pt (empresas)
Consulta pública gratuita de dados empresariais (nome, morada, estado).

| Intervalo | Máximo |
|------------|---------|
| Minuto | 1 |
| Hora | 10 |
| Dia | 100 |
| Mês | 1000 |

---

## ⚖️ Considerações
- Só valida estrutura, não existência real.  
- Dados de pessoas singulares são protegidos (RGPD).  
- Dados de empresas são públicos (nif.pt).

---

**Fim do documento**
