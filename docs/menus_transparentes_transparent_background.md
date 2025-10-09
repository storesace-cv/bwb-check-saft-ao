# Exportação dos menus com fundo transparente

Este guia descreve como os menus da aplicação Ferramentas SAF-T (AO) foram configurados para coexistirem com a janela semi-transparente, permitindo reutilizar a solução noutros repositórios geridos pelo Codex. A abordagem foi pensada para que apenas o nome dos recursos gráficos precise de ser ajustado.

## 1. Janela principal preparada para transparência

1. A `MainWindow` é criada como `QMainWindow` sem moldura (`FramelessWindowHint`) e com os atributos `WA_TranslucentBackground` e `WA_NoSystemBackground`, para que o sistema operativo respeite o canal alfa. A janela desactiva também o `autoFillBackground`. 【F:src/saftao/gui.py†L1046-L1054】
2. O conteúdo visível vive dentro de um `BackgroundLayerWidget` que desenha a imagem ou cor de fundo com suporte a transparência, mantendo a lógica separada do resto da interface. 【F:src/saftao/gui.py†L1004-L1042】
3. Cada página registada no `QStackedWidget` recebe os mesmos atributos de transparência, garantindo que nenhuma área opaca se sobrepõe ao corpo da janela quando o utilizador muda de menu. 【F:src/saftao/gui.py†L1096-L1130】【F:src/saftao/gui.py†L1156-L1169】

Ao copiar esta configuração para outro projecto, certifique-se de que a nova `MainWindow` replica estes atributos e o padrão de encapsular o conteúdo num widget dedicado ao fundo.

## 2. Barra de menus integrada no corpo transparente

1. Após criar a janela, o código obtém a `QMenuBar` padrão e força `setNativeMenuBar(False)`. Isto evita que o menu passe para a barra global do macOS e garante que permanece dentro da janela semi-transparente em todas as plataformas. 【F:src/saftao/gui.py†L1138-L1146】
2. A barra é mostrada explicitamente com `show()` para que herde o mesmo plano de fundo translucido do `BackgroundLayerWidget`. 【F:src/saftao/gui.py†L1146-L1147】
3. Os menus (`QMenu`) são criados através de `_build_menus`, que apenas adiciona acções e liga cada uma ao `QStackedWidget`. Esta separação facilita replicar os menus noutros projectos, bastando actualizar as chaves alvo (`validation`, `fix_standard`, etc.). 【F:src/saftao/gui.py†L1178-L1226】

## 3. Folha de estilos com opacidade controlada

A folha de estilos global (`APP_STYLESHEET`) define transparência parcial para `QMainWindow`, `QMenuBar` e `QMenu`, proporcionando um aspecto consistente sobre o fundo. Reutilize estas regras no novo repositório ou adapte os valores RGBA consoante a imagem de fundo. 【F:src/saftao/ui/app_launcher.py†L30-L59】

```css
QMainWindow, QDialog {
    background: rgba(255, 255, 255, 230);
}
QMenuBar {
    background-color: rgba(255, 255, 255, 210);
}
QMenu {
    background-color: rgba(255, 255, 255, 245);
}
```

## 4. Encaminhamento das acções para páginas transparentes

1. `_add_menu_action` associa cada item de menu a um `lambda` que chama `_show_page` com a chave correcta. Isto evita lógica adicional por acção e facilita renomear destinos ao adaptar a interface. 【F:src/saftao/gui.py†L1218-L1226】
2. `_show_page` troca o índice activo no `QStackedWidget`, que já está configurado para fundo transparente (`WA_TranslucentBackground` + `background-color: transparent`). Assim, quando uma página é apresentada, o utilizador continua a ver a imagem através das áreas não preenchidas. 【F:src/saftao/gui.py†L1076-L1085】【F:src/saftao/gui.py†L1161-L1169】

## 5. Passos para reutilização noutro repositório

1. Copie a implementação da `MainWindow`, do `BackgroundLayerWidget` e das páginas relevantes (ou adapte a estrutura para as páginas do novo projecto).
2. Transporte a constante `APP_STYLESHEET` — ou pelo menos as secções `QMainWindow`, `QMenuBar` e `QMenu` — para a nova aplicação e aplique-a após criar o `QApplication`.
3. Replique a estratégia de carregar a imagem de fundo através do `BackgroundLayerWidget`. Se o ficheiro tiver outro nome, altere apenas a constante `BACKGROUND_IMAGE` no novo repositório.
4. Ajuste a lista de menus e acções em `_build_menus` para corresponder às ferramentas da nova aplicação, mantendo o padrão de chaves/textos e a ligação ao `QStackedWidget`.
5. Teste em macOS, Windows e Linux para garantir que `setNativeMenuBar(False)` mantém a barra embutida na janela e que as opacidades desejadas são respeitadas pelo compositor de cada sistema.

Seguindo estes passos, os menus permanecerão funcionais e visíveis sobre o fundo transparente, mesmo após exportar o código para outro repositório com recursos renomeados.
