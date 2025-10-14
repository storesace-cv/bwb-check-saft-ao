# Guia de replicação do ecrã inicial e ambiente transparente

> ⚠️ **Nota histórica**
> A interface actual do projecto foi migrada para Tkinter e já não depende de
> Qt/PySide. O conteúdo abaixo é mantido apenas como referência sobre a
> implementação anterior.

Este documento descreve os passos exatos aplicados no projeto BWB Fichas Técnicas Vínicas (FTV) para criar o splash screen inicial e garantir um ambiente transparente na aplicação PyQt5. O objetivo é permitir replicar a mesma experiência visual noutro repositório.

## 1. Preparação do ambiente Qt

1. **Configuração do QApplication partilhado**  
   Utilize a função `ensure_ftv_app` para garantir que existe uma instância global de `QApplication`, aplicar o tema partilhado e definir a folha de estilos global. A função também garante que o atributo `Qt.AA_ShareOpenGLContexts` está definido antes da criação da aplicação, algo necessário para componentes `QtWebEngine`. 【F:ui/app_launcher.py†L41-L95】

2. **Bootstrap das bibliotecas Qt**  
   Importe `qt_bootstrap` o mais cedo possível no ponto de entrada do executável para configurar automaticamente as variáveis de ambiente ligadas aos plugins Qt (por exemplo `QT_QPA_PLATFORM_PLUGIN_PATH`). No projeto original isto é feito com `import qt_bootstrap  # noqa: F401` no topo de `bwb-fichas_tecnicas.py`. 【F:bwb-fichas_tecnicas.py†L9-L18】

## 2. Implementação do splash screen

1. **Classe dedicada `SplashScreen`**  
   Crie uma subclasse de `QDialog` que representa o splash screen. A implementação atual encontra-se em `ui/splashscreen.py`. A classe configura-se da seguinte forma:
   - Define a flag `Qt.SplashScreen | Qt.FramelessWindowHint` para obter uma janela sem moldura que aparece como splash.  
   - Ativa o atributo `Qt.WA_TranslucentBackground` e aplica `background: transparent;` para que o diálogo respeite o canal alfa da imagem.  
   - Define um tamanho fixo (`800x500`) e carrega o pixmap `bwb-Splash.png` para um `QLabel` de fundo.  
   - Permite sobrepor mensagens dinâmicas e botões através dos métodos `show_message`, `add_button_box` e `overlay`. 【F:ui/splashscreen.py†L12-L67】

2. **Imagem do splash**  
   Armazene a imagem (`bwb-Splash.png`) na mesma pasta do módulo para facilitar o `QPixmap(Path(__file__).with_name("bwb-Splash.png"))`. Isto evita caminhos absolutos e garante portabilidade. 【F:ui/splashscreen.py†L21-L26】

3. **Comportamento de clique**  
   Sobreponha `mousePressEvent` para fechar o splash e emitir o sinal `clicked`. Isto permite que o utilizador avance manualmente caso não haja tarefas pendentes. 【F:ui/splashscreen.py†L29-L34】

## 3. Integração no fluxo de arranque

1. **Criação e exibição do splash**  
   No entrypoint (`bwb-fichas_tecnicas.py`), instancie `SplashScreen()` após obter o `QApplication`. Se existirem migrações pendentes de base de dados, mostre uma mensagem sobreposta (`show_message("A migrar base de dados…")`), processe os eventos para atualizar o UI e feche o splash assim que a operação terminar. Caso contrário, execute o diálogo de forma modal usando `exec_modal(splash)` para permitir ao utilizador fechar o splash quando estiver pronto. 【F:bwb-fichas_tecnicas.py†L60-L86】【F:ui/qt_compat.py†L17-L33】

2. **Processamento de eventos durante tarefas longas**  
   Chamar `app.processEvents()` logo após `show_message` garante que a mensagem é renderizada antes de iniciar as migrações, evitando que o ecrã pareça congelado. 【F:bwb-fichas_tecnicas.py†L67-L74】

3. **Continuação do arranque**  
   Depois de fechar o splash, continue com a inicialização do `DataStore`, importação de alergénios e arranque da janela principal via `launch_ftv_app`. Isto mantém o splash isolado do resto da lógica de arranque. 【F:bwb-fichas_tecnicas.py†L88-L147】【F:ui/app_launcher.py†L97-L117】

## 4. Ambiente transparente

1. **Janela sem moldura e com fundo transparente**  
   O splash utiliza `Qt.WA_TranslucentBackground` e um estilo `background: transparent;` tanto no diálogo como no `QLabel` de fundo. Estas definições garantem que os cantos arredondados e o canal alfa da imagem são respeitados pelo sistema operativo. 【F:ui/splashscreen.py†L18-L27】

2. **Folha de estilos global**  
   A função `ensure_ftv_app` carrega `APP_STYLESHEET` de `ui_editor_fonte`, que define um tema consistente com transparências controladas para outros widgets. Ao replicar o setup, assegure-se de carregar a folha de estilos desejada imediatamente após criar a `QApplication`. 【F:ui/app_launcher.py†L77-L95】

## 5. Passos para replicar noutro repositório

1. Copie `ui/splashscreen.py` e a imagem `bwb-Splash.png` (ou substitua por uma imagem com transparência própria). Ajuste o caminho e dimensões se necessário.
2. Importe `SplashScreen` no entrypoint principal e integre a lógica apresentada na secção 3. Adapte as mensagens e condições ao fluxo do novo projeto.
3. Garanta que o módulo responsável por bootstrap (`qt_bootstrap.py` ou equivalente) é importado antes de qualquer uso de Qt para que o ambiente seja corretamente configurado.
4. Se o novo projeto já possuir um gestor de estilos, adicione as regras de transparência adequadas (`background: transparent;`, remoção de bordas) para os widgets envolvidos.
5. Teste em cada sistema operativo suportado para confirmar que o splash respeita a transparência e que o arranque não bloqueia a interface.

Seguindo estes passos, o outro repositório terá o mesmo comportamento visual e funcional do splash screen com ambiente transparente implementado no FTV.
