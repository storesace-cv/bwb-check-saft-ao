# Exportação do splash screen com fundo transparente

Este documento descreve, passo a passo, como a aplicação Ferramentas SAF-T (AO) renderiza a imagem de fundo do *splash screen* mantendo a transparência. A estrutura foi pensada para ser reutilizada noutros repositórios geridos pelo Codex, bastando ajustar o nome do ficheiro da imagem.

## 1. Localização e carregamento da imagem

1. A imagem do *splash* é armazenada na mesma pasta que o módulo `splashscreen.py`, permitindo construir o caminho com `Path(__file__).with_name(...)` sem depender de caminhos absolutos. 【F:src/saftao/ui/splashscreen.py†L18-L44】
2. Ao instanciar `QPixmap`, o código verifica se o ficheiro existe; caso contrário, mostra texto alternativo. Esta verificação facilita a reutilização noutros repositórios onde o nome da imagem pode mudar. 【F:src/saftao/ui/splashscreen.py†L46-L50】

Para usar outra imagem, copie o ficheiro para a pasta `src/saftao/ui/` (ou equivalente no novo projeto) e ajuste a constante `SPLASH_IMAGE_PATH` para refletir o novo nome.

## 2. Transparência do *splash*

1. A janela é criada como `Qt.SplashScreen | Qt.FramelessWindowHint` e recebe o atributo `Qt.WA_TranslucentBackground`. Isso permite que o canal alfa do PNG seja respeitado pelo compositor do sistema operativo. 【F:src/saftao/ui/splashscreen.py†L29-L35】
2. Tanto o diálogo como o `QLabel` de fundo recebem `background: transparent;` via `setStyleSheet`, garantindo que nenhum preenchimento opaco se sobrepõe à imagem. 【F:src/saftao/ui/splashscreen.py†L34-L44】
3. O `overlay` onde aparecem mensagens e botões também tem fundo transparente (`QWidget#splash-overlay` na folha de estilos). Assim, qualquer widget adicional respeita a transparência do plano de fundo. 【F:src/saftao/ui/splashscreen.py†L52-L84】【F:src/saftao/ui/app_launcher.py†L72-L78】

## 3. Folha de estilos global

A função `ensure_app` aplica a folha de estilos `APP_STYLESHEET`, que define regras específicas para o *splash*:

- `QLabel#splash-background { background: transparent; }`
- `QWidget#splash-overlay { background: transparent; }`

Estas regras complementam as `setStyleSheet` locais e asseguram que o mesmo comportamento é reproduzido se o widget for reinstanciado noutro contexto. 【F:src/saftao/ui/app_launcher.py†L30-L124】

## 4. Reutilização noutro repositório

Para replicar a solução com um nome de imagem diferente:

1. Copie `src/saftao/ui/splashscreen.py` e a folha de estilos presente em `APP_STYLESHEET` (ou extraia apenas as regras relativas ao *splash*).
2. Adicione a nova imagem (por exemplo `nova-imagem.png`) à mesma pasta e atualize `SPLASH_IMAGE_PATH = Path(__file__).with_name("nova-imagem.png")`.
3. Garanta que o `QApplication` partilhado aplica a folha de estilos contendo os seletores `#splash-background` e `#splash-overlay`.
4. Se necessário, ajuste `setFixedSize(...)` para corresponder às dimensões do novo ficheiro.
5. Valide que `QPixmap` consegue carregar a imagem (por exemplo, via testes ou logs) e que o canal alfa está preservado no ficheiro PNG exportado.

Seguindo estes passos, a imagem de fundo permanecerá transparente no *splash screen*, mesmo quando clonada para outro projeto com ficheiros renomeados.
