# FrontEngine

<p align="center">
  <a href="../README.md">English</a> ·
  <a href="README_zh-TW.md">繁體中文</a> ·
  <a href="README_zh-CN.md">简体中文</a> ·
  <a href="README_ja.md">日本語</a> ·
  <a href="README_ko.md">한국어</a> ·
  <a href="README_es.md">Español</a> ·
  <a href="README_fr.md">Français</a> ·
  <a href="README_de.md">Deutsch</a> ·
  <strong>Português (BR)</strong> ·
  <a href="README_ru.md">Русский</a>
</p>

[![CI](https://github.com/JeffreyChen-SteamProjects/FrontEngine/actions/workflows/ci.yml/badge.svg)](https://github.com/JeffreyChen-SteamProjects/FrontEngine/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/frontengine)](https://pypi.org/project/frontengine/)
[![Python](https://img.shields.io/pypi/pyversions/frontengine)](https://pypi.org/project/frontengine/)

**Coloque qualquer coisa sobre a sua tela — ou por baixo dela.**

O FrontEngine é um aplicativo de sobreposição para desktop. Vídeo, imagens,
GIFs, páginas web, texto, partículas, som e um mascote animado podem ser
colocados sobre todas as outras janelas (com clique passante, então o que está
por baixo continua funcionando), ou atrás delas como um papel de parede ao vivo.
Em torno disso há um conjunto de ferramentas para a própria tela: filtros de
conforto visual, anotação em apresentações, medição e captura, máscaras de foco
e widgets de área de trabalho.

[Apoie este projeto na Steam](https://store.steampowered.com/app/2793470/FrontEngine/)
 · [Documentação](https://frontengine.readthedocs.io/en/latest/)
 · [Assista a uma demonstração](https://youtu.be/fewogcb3b8Y)

![FrontEngine UI](../image/FrontEngine.png)

---

## Instalação

Python **3.10+**. O Windows 10/11 é o alvo principal; o macOS e o Linux executam
o aplicativo, com as diferenças de plataforma listadas em [Suporte de plataforma](#suporte-de-plataforma).

```bash
pip install frontengine

frontengine                    # or: python -m frontengine
frontengine --preset "Work"    # apply a saved preset on launch
```

Binários pré-compilados para Windows estão na
[página de Releases](https://github.com/JeffreyChen-SteamProjects/FrontEngine/releases),
e a versão da Steam entrega o mesmo aplicativo com suporte à Workshop.

> **Saindo.** As sobreposições podem cobrir a tela inteira, incluindo a própria
> janela do FrontEngine, então há duas saídas de emergência que não precisam do
> mouse: `Ctrl+Shift+F12` fecha todas as sobreposições, e **F12 encerra o
> aplicativo por completo** de qualquer lugar (somente Windows — veja *Ajuda →
> Como forçar o fechamento*).

---

## O que ele coloca na tela

A barra lateral agrupa as páginas conforme a finalidade delas. Esta seção segue
essa organização.

### Na tela

Sobreposições de mídia. Cada uma escolhe seu monitor (ou abrange todos eles),
lembra onde você a arrastou e tem sua própria opacidade.

- **Vídeo** — com volume, taxa de reprodução e repetição.
- **Imagem** — uma única figura, uma pasta como apresentação de slides, ou um
  **quadro de referência**: várias imagens em uma tela, cada uma arrastável, com
  o quadro inteiro podendo receber zoom e ser deslocado.
- **Web** — uma URL ou um arquivo HTML local, opcionalmente interativo. O **modo
  painel** alterna por uma lista de URLs, para que um display de parede possa
  percorrer páginas por uma tecla de atalho ou um temporizador.
- **GIF / WebP** — animações com velocidade ajustável.
- **Texto** — fonte, cor, contorno, alinhamento e um letreiro rolante, mostrando
  ou uma cadeia fixa ou uma **fonte ao vivo**: relógio, data, contagem
  regressiva, cronômetro, carga do sistema ou o clima. As fontes ao vivo usam um
  modelo `{field}`, e a página lista os campos que cada uma oferece.
- **Som** — reprodução de música e efeitos WAV de baixa latência.
- **Cena** — combine vários dos itens acima em uma única composição descrita por
  um documento JSON que você pode salvar e compartilhar.
- **Partícula** — um efeito de partículas em OpenGL.

<details>
<summary>Capturas de tela (os GIFs podem levar um momento para carregar)</summary>

| GIF | WebP |
| --- | --- |
| ![GIF](../gifs/play_gif.gif) | ![WEBP](../gifs/webp.gif) |

| Vídeo | Site |
| --- | --- |
| ![Video](../gifs/video.gif) | ![Website](../gifs/website.gif) |

</details>

### Área de trabalho

**Mascote de desktop** — um sprite animado que vive na sua área de trabalho.

- **Sprites** — um único GIF/WebP/PNG, ou uma pasta *pet pack* cujos nomes de
  arquivo mapeiam para estados: `walk`, `idle`, `sleep`, `climb`, `fall`, `drag`
  (um estado ausente recai em `walk`). Um `pet.json` opcional define tamanho,
  velocidade e se ele pode escalar, falar ou sentar em janelas.
- **Comportamento** — anda pelo chão com gravidade (arremesse-o e ele quica),
  vagueia livremente, ou persegue o cursor. Mascotes de chão escalam as bordas
  da tela e ficam de pé na borda superior de outras janelas.
- **Vida** — humor, saciedade e um nível de afeição que persistem entre
  execuções. Ele cresce conforme sobe de nível, fala em balões de fala, tira
  cochilos enquanto você está ausente e avisa sobre bateria fraca.
- **Interação** — arraste-o, clique com o botão direito para clonar / alimentar
  / definir um lembrete, e **solte um arquivo sobre ele**: uma imagem ou pet
  pack vira sua nova aparência, qualquer outra coisa é comida. O que ele come
  importa — um arquivo compactado é um banquete, música o anima mais do que o
  enche, um documento é uma refeição modesta, um binário é difícil demais de
  mastigar.
- **Pega-pega** — com dois ou mais mascotes na tela, marque *Brincar de pega-pega
  entre si* e um se torna o "pegador": ele caminha em direção ao vizinho mais
  próximo enquanto os outros correm na direção oposta, e pegar alguém passa a
  vez adiante.
- **Reage ao som** — o mascote pulsa com a saída dos seus alto-falantes, ou com
  o seu **microfone** para que se mexa enquanto você fala. Ambos leem apenas o
  *medidor* de saída — um número, não áudio. Os picos são suavizados com uma
  janela RMS e um envelope de ataque rápido/decaimento lento, para que a
  pulsação respire em vez de tremular. Com vários monitores, cada mascote segue
  o ponto de saída de áudio correspondente à sua própria tela.
- **Temporizador de foco** — um pomodoro na mesma página, anunciado pelo
  mascote: ele avisa quando o foco termina e quando a pausa acabou.
- **Chat** — o mascote pode responder você por meio do Claude quando
  `ANTHROPIC_API_KEY` está definido. Desativado a menos que você o habilite;
  veja [O que sai da máquina](#o-que-sai-da-máquina).

**Papel de parede** — reproduza uma pasta de imagens e animações *por baixo* de
cada janela. Cada monitor aponta para sua própria pasta com seu próprio
temporizador, embaralhada ou lida recursivamente, e pode pulsar com o nível dos
alto-falantes. Uma segunda pasta pode assumir durante as horas de silêncio.

**Widgets** — quatro coisas que ficam na área de trabalho:

- **Espectro de áudio** — barras ou um anel, bandas espaçadas em escala
  logarítmica, suavizadas com um seguidor de ataque rápido/decaimento lento e
  marcadores de pico que descem gradualmente.
- **Tocando agora** — a faixa atual dos controles de mídia do Windows quando os
  bindings opcionais `winsdk` estão instalados; caso contrário, o nome do
  aplicativo que está de fato produzindo som.
- **Monitor do sistema** — CPU, memória, disco, bateria e taxa de transferência
  de rede como pequenos sparklines; marque as linhas que você quiser. Uma média
  esconde uma paralisação; uma linha não. Uma linha oculta continua registrando,
  então reativá-la mostra o que aconteceu nesse meio-tempo.
- **Notas adesivas** — cartões editáveis acima de cada janela, mantendo seu
  texto, cor e posição entre sessões.

### Trabalho

**Foco** — duas sobreposições para quando a tela compete com o seu trabalho.
*Escurecer janelas de fundo* sombreia tudo, exceto a janela em que você está
trabalhando, com intensidade ajustável. *Cobrir uma distração* mascara uma faixa
da tela: a barra de tarefas, um canto de notificações, uma borda, ou tudo. Ambas
deixam os cliques passar, então o que elas cobrem continua funcionando — apenas
para de puxar o seu olhar.

**Cuidado com a tela** — para sessões longas diante da tela:

- **Filtro de cor** — sete tonalidades, do quente passando por âmbar e rosa até
  o cinza, com intensidade ajustável.
- **Régua de leitura** — escurece a página e deixa uma faixa clara que segue o
  cursor.
- **Lembrete de pausa** — a regra 20-20-20, com uma sobreposição de descanso
  quando o intervalo se completa.
- **Simulação de visão de cores** — protanopia, deuteranopia, tritanopia e
  acromatopsia com severidade ajustável, usando o modelo de Machado et al.
  (2009). Diferentemente das outras sobreposições, esta é opaca, porque mostrar
  o que outra pessoa vê significa repintar a tela em vez de matizá-la.

**Apresentação** — para demonstrações, aulas e gravações:

- **Anotação** — desenhe sobre a tela com uma caneta, um marca-texto ou uma
  borracha, com desfazer e limpar.
- **Efeitos de cursor** — um anel ao redor do ponteiro, uma ondulação ao clicar
  e um holofote que escurece todo o resto.
- **Exibição de teclas** — mostra o que você acabou de pressionar, e qual botão
  do mouse você clicou, para que os espectadores possam acompanhar; some após
  alguns segundos. Escolha onde o painel fica e o tamanho do texto, e desative os
  cliques do mouse separadamente.
- **Lupa** — uma visão ampliada da área ao redor do cursor.
- **Quadro branco** — uma tela infinita: arraste para deslocar, role para dar
  zoom, salve o que você desenhou. Os traços vivem em coordenadas da tela, então
  deslocar e dar zoom os deixa onde eles pertencem.
- **Congelar** — fixe o quadro atual de um monitor para que você possa continuar
  trabalhando atrás de uma imagem parada. `Ctrl+Shift+F7` a libera, o que importa
  porque a imagem congelada cobre o botão que faria isso.

**Ferramentas** — medição, captura e manuseio de janelas:

- **Conta-gotas de cor / régua de pixels / transferidor** — clique para
  amostrar ou medir; o resultado vai direto para a área de transferência como
  `#rrggbb`, `rgb(...)`, `hsl(...)` ou uma propriedade personalizada de CSS.
- **Captura de região** — arraste para delimitar uma área; ela vai para a área
  de transferência, pode ser salva em um arquivo, ou **fixada** por cima como uma
  cópia flutuante com zoom.
- **Gravar área** — grave uma região em um GIF animado, com a câmera composta no
  canto para o visual de vídeo de reação. Limitado tanto pela duração quanto pela
  contagem de quadros, porque cada quadro é mantido na memória.
- **Câmera** — a sua webcam em um círculo, caixa arredondada ou retângulo,
  exibida localmente e nunca gravada. Qualquer entrada de vídeo funciona,
  incluindo placas de captura, e a lista de dispositivos se atualiza sem
  reiniciar, já que as placas normalmente são conectadas enquanto o aplicativo
  já está em execução.
- **Câmera virtual** — envie uma região, com sobreposições e tudo, como uma
  webcam que o Zoom, o Teams ou o Discord possam selecionar como sua fonte de
  vídeo. Precisa do pacote opcional `pyvirtualcam` e de um driver de câmera
  virtual (o OBS instala um); sem um deles, o botão diz isso em vez de falhar
  silenciosamente.
- **Ler texto** — arraste para delimitar uma área para copiar o texto nela,
  traduzi-lo ou fazer uma pergunta sobre ele. Este envia a seleção para fora da
  máquina; veja [O que sai da máquina](#o-que-sai-da-máquina).
- **Fixar uma janela** — mantenha a janela de outro programa por cima, ou
  atenue-a, enquanto você trabalha diante dela. Apenas o empilhamento e a
  opacidade são tocados, nunca o conteúdo da janela.
- **Réplica de janela** — uma pequena cópia ao vivo sempre no topo de outra
  janela, para que você possa acompanhar uma renderização ou um chat enquanto
  ele está soterrado.
- **Layouts de janela** — salve onde cada janela fica e recoloque-as depois. As
  janelas são identificadas pelo título; uma que não esteja na tela é ignorada
  em vez de ser adivinhada.

---

## Controlando tudo de uma vez

A página **Central de controle** alcança cada sobreposição em cada página, seja
qual for a aba que a abriu: ocultar, mostrar, fechar, silenciar, travar,
redefinir posições, ajustar a opacidade em passos, e aplicar um **nível de
qualidade** (alto / equilibrado / economia) que limita a taxa de atualização de
cada sobreposição e reduz sua resolução de renderização. Ela também carrega um
fundo de chroma-key para o OBS, uma opção *Ocultar da captura*, o painel de logs
e **Fixar nesta área de trabalho** — as sobreposições saem de cena quando você
troca de área de trabalho virtual e retornam quando você volta. Desafixar traz
de volta o que quer que ela tenha guardado.

Teclas de atalho globais padrão, todas reconfiguráveis em **Configurações →
Teclas de atalho**:

| Atalho | Ação |
| --- | --- |
| `Ctrl+Shift+F12` | Fechar todas as sobreposições |
| `Ctrl+Shift+F11` / `F10` | Ocultar / mostrar todas as sobreposições |
| `Ctrl+Shift+F9` | Silenciar tudo |
| `Ctrl+Shift+↑` / `↓` | Aumentar / diminuir opacidade |
| `Ctrl+Shift+L` | Travar ou destravar (clique passante vs. arrastável) |
| `Ctrl+Shift+→` | Próxima página do painel |
| `Ctrl+Shift+F8` | Mostrar a folha de atalhos na tela |
| `Ctrl+Shift+F7` | Congelar / descongelar a tela |
| `Ctrl+Shift+F6` / `F5` / `F4` | Reproduzir/pausar mídia, próxima e faixa anterior |
| `Ctrl+Shift+F3` | Mover a janela em primeiro plano para o próximo monitor |
| `F12` | Sair imediatamente (Windows) |

O transporte de mídia envia as teclas de mídia do sistema, então alcança
qualquer reprodutor que as escute. Mover uma janela mantém suas proporções em
vez de encaixá-la, que é o que o próprio `Win+Shift+Arrow` do Windows faz.

As mesmas ações — e nada além delas — são o que os controles remotos acionam:

- **Seu telefone** (Configurações → Controle remoto) — o FrontEngine serve uma
  pequena página na sua rede local; abra o link em um telefone e os botões
  acionam essas ações.
- **Um controlador MIDI** — pressione *Aprender*, mova um botão giratório ou um
  pad, e vincule-o. Ele usa o winmm embutido do Windows, então nenhum pacote
  extra é necessário. Um botão giratório dispara assim que chega ao topo, em vez
  de repetidamente no caminho, e soltar um pad não conta como um segundo
  pressionamento.

---

## Predefinições e automação

As **Predefinições** capturam as configurações de todas as páginas de uma vez.
Salve, carregue, exclua, exporte e importe-as no menu **Predefinições**, aplique
uma na inicialização, ou restaure a sessão anterior automaticamente. Uma
predefinição pode ser exportada como um **pacote** — um zip que carrega a mídia
que ela referencia — para que abra em uma máquina que não tem esses arquivos.

Coisas que então decidem por si mesmas, todas a partir do menu **Configurações**.
A pausa inteligente é a única que já vem ligada; todo o resto fica desligado até
você acioná-lo.

| | |
| --- | --- |
| **Regras** | *"Quando estas condições se mantiverem, faça isto."* Combine um dia da semana, uma faixa de horário e qual aplicativo está em foco, então aplique uma predefinição, oculte/mostre/feche as sobreposições, ou defina a qualidade. Uma condição em branco significa "qualquer", e uma regra é executada **uma vez** quando suas condições começam a se manter, em vez de repetidamente enquanto se mantêm. Este é o único lugar onde as condições se compõem; as linhas abaixo conhecem cada uma um único tipo. |
| **Pausa inteligente** | Recolha as sobreposições enquanto um aplicativo em tela cheia estiver rodando, enquanto a máquina estiver na bateria, ou enquanto um aplicativo nomeado estiver em foco. *(Ligada por padrão, para a regra de tela cheia.)* |
| **Perfis de aplicativo** | Aplique uma predefinição quando você mudar para um determinado aplicativo. |
| **Agenda de predefinições** | Aplique uma predefinição em dias da semana escolhidos, em um horário definido. |
| **Agenda de tema** | Alterne entre um tema de dia e um de noite pelo relógio. |
| **Modo sinalização** | Alterne uma lista de predefinições em um temporizador com a janela principal guardada, para uma máquina deixada em execução como display. |
| **Protetor de tela** | Após um limite de inatividade, exiba o vídeo / imagem / GIF / partícula / página web que você escolheu, e retire-o quando você voltar. |
| **Lembretes** | A cada N minutos, ou uma vez por dia em um horário definido, mostrados como um aviso que se fecha sozinho. |
| **Manter ativo** | Impeça o display de dormir enquanto as sobreposições estiverem ativas. |
| **Iniciar com o sistema** | Iniciar ao fazer login. |
| **Tempo de tela** | Quais aplicativos estiveram em foco e por quanto tempo, com um detalhamento diário e um resumo de sete dias. Ele pausa enquanto você está longe do teclado, mantém no máximo 60 dias, e limpar exclui o próprio arquivo. |
| **Histórico da área de transferência** | Pesquise o que você copiou e fixe as frases que você reutiliza. As áreas de transferência frequentemente guardam senhas, então isto é mantido **apenas na memória** a menos que você marque separadamente "manter entre sessões". |

---

## Idiomas

Sete: English, 繁體中文, 简体中文, Deutsch, Русский, Français, Italiano.

Escolha um no menu **Idioma** e a interface muda **imediatamente** — sem
reiniciar. O que quer que você tivesse aberto permanece aberto: as sobreposições
continuam rodando, e as configurações de cada página são deixadas exatamente
como estavam. Em uma instalação da Steam, a primeira inicialização segue o
próprio idioma do cliente Steam.

---

## Notas de privacidade e plataforma

### O que sai da máquina

Tudo no FrontEngine é local, a menos que esteja nesta lista. Há quatro exceções,
todas por opção do usuário (opt-in):

| Recurso | Para onde vai | Proteção |
| --- | --- | --- |
| **Ler texto** (Ferramentas) | A região selecionada é enviada para a API da Anthropic | Pergunta uma vez antes do primeiro envio e lembra a resposta; o consentimento pode ser retirado na janela de resultado. Usa a sua própria `ANTHROPIC_API_KEY`, lida do ambiente e nunca gravada em um arquivo de configuração. Nada é enviado sem ambos. |
| **Chat do mascote** | Sua mensagem vai para a API da Anthropic | Mesma chave, mesma regra; desligado por padrão. |
| **Clima** (fonte de texto) | As coordenadas vão para o Open-Meteo | Sem chave, sem conta, sem dados identificáveis; apenas o que você digitou como localização. |
| **Controle remoto por telefone** | Serve uma página na sua rede local | Desligado por padrão. O link carrega um token regenerado a cada início, então um link antigo para de funcionar, e a página só pode solicitar a lista fixa de ações. É HTTP simples: outra pessoa na mesma rede poderia ler o token e pressionar os mesmos botões — um incômodo, e não uma violação, dado o que esses botões fazem, mas deixe-o desligado em redes em que você não confia. |

Os recursos de áudio leem apenas um **medidor** de saída — um único número —
exceto o espectro, que precisa de amostras reais para calcular frequências e
assim captura o fluxo de saída do sistema. Essas amostras são analisadas na
memória, nunca gravadas em disco ou enviadas para lugar algum, e a captura para
no momento em que você para o espectro.

**Plugins** são Python e rodam com os mesmos privilégios que o FrontEngine —
eles não podem ser isolados em sandbox. O carregamento fica desligado por padrão
(Configurações → Carregar plugins), cada carregamento é registrado, e um plugin
quebrado é ignorado em vez de parar o aplicativo. Instale apenas plugins em que
você confia.

### Privacidade em compartilhamento de tela

Suas sobreposições são para você, não para as pessoas com quem você está
compartilhando. Em **Configurações → Privacidade em compartilhamento de tela**,
o FrontEngine pode retirá-las da captura enquanto um aplicativo de reunião
estiver aberto:

- **Elas permanecem na sua própria tela.** Apenas a cópia capturada fica em
  branco — isto usa o `WDA_EXCLUDEFROMCAPTURE` do Windows, uma flag de nível de
  SO que aplicativos de conferência e gravadores respeitam.
- **As máscaras são a exceção.** Uma máscara de distração existe para cobrir
  algo, então ela deliberadamente permanece visível na captura.
- **O gatilho é a sua lista.** O Windows não tem uma API confiável de "estou
  sendo capturado", então ele observa os títulos de janela que você nomeia — o
  que também pega uma reunião realizada em uma aba de navegador, onde o
  executável é apenas o navegador.

Há também um botão manual *Ocultar da captura* na central de controle.

> Isto é privacidade, não segurança: derrota o caminho comum de captura, e nunca
> esconde nada da pessoa sentada à mesa.

### Suporte de plataforma

Tudo o que não estiver listado aqui funciona nas três plataformas.

| Recurso | Windows | macOS | Linux |
| --- | :---: | :---: | :---: |
| Sobreposições, mascote, papel de parede, apresentação, cuidado com a tela, captura, gravação | ✅ | ✅ | ✅ |
| Reação ao áudio, espectro, sincronia labial (WASAPI) | ✅ | — | — |
| Tocando agora (controles de mídia) | ✅ | — | — |
| Fixar / atenuar outra janela, layouts de janela, réplica ao vivo | ✅ | — | — |
| Ocultar sobreposições da captura de tela | ✅ | — | — |
| Controle MIDI (winmm) | ✅ | — | — |
| Teclas de transporte de mídia | ✅ | — | — |
| Fixar sobreposições em uma área de trabalho virtual | ✅ | — | — |
| Mover uma janela para o próximo monitor | ✅ | — | — |
| Saída de emergência `F12` | ✅ | — | — |
| Escurecer o fundo ao redor da janela *ativa* | ✅ | tela inteira | tela inteira |
| Mascote de pé sobre outras janelas | ✅ | — | com `wmctrl` |

Onde um recurso não pode funcionar, o botão diz isso em vez de falhar
silenciosamente.

---

## Estendendo

- **Steam Workshop** — itens inscritos são captados da própria pasta
  `steamapps/workshop/content` da Steam: predefinições são importadas e pet packs
  são listados com seus caminhos, em **Predefinições → Importar conteúdo da
  Workshop**. Publicar na Workshop precisa do SDK do Steamworks e não é embutido.
- **Plugins** — uma pasta `plugins/` pode adicionar suas próprias abas, seja por
  meio de um mapeamento `FRONTENGINE_TABS = {"name": WidgetClass}` ou de um gancho
  `register(registry)`. Leia primeiro a nota de confiança acima.

---

## Desenvolvimento

```bash
pip install -r dev_requirements.txt
pip install -e .

python -m pytest tests/ -q          # the whole suite, headless (Qt offscreen)
```

A verificação estática usa o pyflakes (em `dev_requirements.txt`), e uma árvore
limpa não imprime nada:

```bash
python -m pyflakes frontengine/ exe/ tests/
```

A suíte de testes roda inteiramente fora da tela e não precisa de display, placa
de som ou câmera; qualquer coisa que toque o mundo externo recebe uma fonte
injetável para que possa ser testada com uma falsa.

- **Arquitetura** — [`architecture_explore.md`](../architecture_explore.md)
  mapeia cada módulo, a estratificação, o contrato de sobreposição e os pontos
  de extensão. Leia-o antes de adicionar uma página ou uma sobreposição: várias
  coisas (o registro da central de controle, sete dicionários de idioma, sete
  árvores de documentação) têm que ser atualizadas juntas, e os testes impõem
  isso.
- **Contribuindo** — veja [`CONTRIBUTING.md`](../CONTRIBUTING.md). Um recurso por
  pull request, todas as verificações de CI verdes.
- **Compilando o executável do Windows** — `python exe/build_exe.py`
  (Nuitka; adicione `--onefile` para um único arquivo).
- **Documentação** — fontes Sphinx em `docs/`, publicadas no
  [Read the Docs](https://frontengine.readthedocs.io/en/latest/) em todos os
  sete idiomas.

---

## Integração contínua e lançamentos

O trabalho flui `feature → dev → main`, e apenas a última etapa publica:

```
feat/xyz  ──PR──►  dev  ──PR──►  main
                    │              │
              CI, no release   CI + release
```

| Workflow | Gatilho | Finalidade |
| --- | --- | --- |
| `CI` (`ci.yml`) | Push / PR para `main` ou `dev`, disparo manual, ou chamado pelo `Nightly` | Compila, roda os testes unitários, depois compila uma wheel a partir *daquele checkout*, instala-a e inicia o aplicativo — em Python 3.10 / 3.11 / 3.12, Windows |
| `Nightly` (`nightly.yml`) | Cron diário, disparo manual | Chama o `CI`. A agenda vive aqui de propósito: o GitHub desabilita workflows que contêm um cron após ~60 dias de inatividade, e isso, de outra forma, derrubaria as verificações de PR junto |
| `Release` (`release.yml`) | Um pull request **a partir de `dev`** é mesclado em `main`, ou disparo manual | Incrementa a versão, faz commit dela de volta com `[skip ci]`, troca `stable.toml` → `pyproject.toml`, compila sdist + wheel, envia ao PyPI como `frontengine`, cria um release no GitHub com a tag `v<version>`, e faz o fast-forward de `dev` |

A publicação acontece **apenas quando `dev` é mesclado em `main`**. Recursos
chegam em `dev` sem cunhar uma versão, e um lançamento é um pull request
deliberado `dev → main`. Um PR de recurso apontado para `main` por engano ainda
assim mescla, mas não publica — a direção da falha é um lançamento faltante, não
um indesejado.

O segmento de patch é incrementado automaticamente; para um lançamento minor ou
major, execute *Actions → Release → Run workflow* e escolha o segmento. Esse
caminho também reexecuta uma publicação que falhou sem precisar de um novo merge.

As versões vivem em dois arquivos: `pyproject.toml` é o pacote de dev
(`frontengine_dev`) e `stable.toml` é o publicado (`frontengine`).

Um segredo de repositório é necessário: `PYPI_API_TOKEN`, um token do PyPI com
escopo para o projeto `frontengine`. O workflow usa `__token__` como o nome de
usuário do twine, então apenas o próprio token precisa ser armazenado.

---

## Licença

Veja [`LICENSE`](../LICENSE). As expectativas da comunidade estão em
[`Contributor_Covenant_Code_of_Conduct.md`](../Contributor_Covenant_Code_of_Conduct.md).
