# FrontEngine

<p align="center">
  <a href="../README.md">English</a> ·
  <a href="README_zh-TW.md">繁體中文</a> ·
  <a href="README_zh-CN.md">简体中文</a> ·
  <a href="README_ja.md">日本語</a> ·
  <a href="README_ko.md">한국어</a> ·
  <strong>Español</strong> ·
  <a href="README_fr.md">Français</a> ·
  <a href="README_de.md">Deutsch</a> ·
  <a href="README_pt-BR.md">Português (BR)</a> ·
  <a href="README_ru.md">Русский</a>
</p>

[![CI](https://github.com/JeffreyChen-SteamProjects/FrontEngine/actions/workflows/ci.yml/badge.svg)](https://github.com/JeffreyChen-SteamProjects/FrontEngine/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/frontengine)](https://pypi.org/project/frontengine/)
[![Python](https://img.shields.io/pypi/pyversions/frontengine)](https://pypi.org/project/frontengine/)

**Pon lo que quieras encima de tu pantalla — o debajo de ella.**

FrontEngine es una aplicación de superposición de escritorio. Vídeo, imágenes, GIFs, páginas
web, texto, partículas, sonido y una mascota animada pueden colocarse sobre cualquier otra
ventana (con paso de clics, de modo que lo que hay debajo sigue funcionando), o detrás de
ellas como un fondo de pantalla animado. Alrededor de eso hay un conjunto de herramientas para
la propia pantalla: filtros de descanso visual, anotación de presentaciones, medición y
captura, máscaras de concentración y widgets de escritorio.

[Apoya este proyecto en Steam](https://store.steampowered.com/app/2793470/FrontEngine/)
 · [Documentación](https://frontengine.readthedocs.io/en/latest/)
 · [Mira una demostración](https://youtu.be/fewogcb3b8Y)

![FrontEngine UI](../image/FrontEngine.png)

---

## Instalación

Python **3.10+**. Windows 10/11 es el objetivo principal; macOS y Linux ejecutan la
aplicación, con las diferencias de plataforma indicadas en [Compatibilidad de plataformas](#compatibilidad-de-plataformas).

```bash
pip install frontengine

frontengine                    # or: python -m frontengine
frontengine --preset "Work"    # apply a saved preset on launch
```

Los binarios precompilados para Windows están en la
[página de Releases](https://github.com/JeffreyChen-SteamProjects/FrontEngine/releases),
y la versión de Steam distribuye la misma aplicación con compatibilidad con el Workshop.

> **Cómo salir.** Las superposiciones pueden cubrir toda la pantalla, incluida la propia
> ventana de FrontEngine, así que hay dos vías de escape que no necesitan el ratón:
> `Ctrl+Shift+F12` cierra todas las superposiciones, y **F12 sale de la aplicación por
> completo** desde cualquier lugar (solo Windows — consulta *Ayuda → Cómo forzar el cierre*).

---

## Lo que pone en pantalla

La barra lateral agrupa las páginas por su propósito. Esta sección la sigue.

### En pantalla

Superposiciones de medios. Cada una elige su monitor (o abarca todos), recuerda dónde la
arrastraste y tiene su propia opacidad.

- **Vídeo** — con volumen, velocidad de reproducción y bucle.
- **Imagen** — una sola imagen, una carpeta como pase de diapositivas, o un **tablero de
  referencia**: varias imágenes en un mismo lienzo, cada una arrastrable, con todo el tablero
  con zoom y desplazamiento.
- **Web** — una URL o un archivo HTML local, opcionalmente interactivo. El **modo panel**
  rota por una lista de URLs, de modo que una pantalla de pared puede recorrer páginas con
  una tecla de acceso rápido o un temporizador.
- **GIF / WebP** — animaciones a una velocidad ajustable.
- **Texto** — fuente, color, contorno, alineación y una marquesina, mostrando ya sea una
  cadena fija o una **fuente en vivo**: reloj, fecha, cuenta atrás, cronómetro, carga del
  sistema o el tiempo meteorológico. Las fuentes en vivo admiten una plantilla `{field}`, y la
  página lista los campos que ofrece cada una.
- **Sonido** — reproducción de música y efectos WAV de baja latencia.
- **Escena** — combina varios de los anteriores en una sola composición descrita por un
  documento JSON que puedes guardar y compartir.
- **Partículas** — un efecto de partículas OpenGL.

<details>
<summary>Capturas de pantalla (los GIFs pueden tardar un momento en cargar)</summary>

| GIF | WebP |
| --- | --- |
| ![GIF](../gifs/play_gif.gif) | ![WEBP](../gifs/webp.gif) |

| Video | Website |
| --- | --- |
| ![Video](../gifs/video.gif) | ![Website](../gifs/website.gif) |

</details>

### Escritorio

**Mascota de escritorio** — un sprite animado que vive en tu escritorio.

- **Sprites** — un solo GIF/WebP/PNG, o una carpeta de *pack de mascota* cuyos nombres de
  archivo se asignan a estados: `walk`, `idle`, `sleep`, `climb`, `fall`, `drag` (un estado
  ausente recurre a `walk`). Un `pet.json` opcional define el tamaño, la velocidad y si puede
  trepar, hablar o sentarse sobre las ventanas.
- **Comportamiento** — caminar por el suelo con gravedad (lánzala y rebota), deambular
  libremente o perseguir el cursor. Las mascotas de suelo trepan por los bordes de la pantalla
  y se posan en el borde superior de otras ventanas.
- **Vida** — estado de ánimo, saciedad y un nivel de afecto que persisten entre ejecuciones.
  Crece al subir de nivel, habla en bocadillos, echa siestas mientras estás fuera y te avisa
  cuando la batería está baja.
- **Interacción** — arrástrala, haz clic derecho para clonar / alimentar / poner un
  recordatorio, y **suelta un archivo sobre ella**: una imagen o un pack de mascota se
  convierte en su nuevo aspecto, cualquier otra cosa se la come. Lo que come importa — un
  archivo comprimido es un festín, la música la anima más de lo que la llena, un documento es
  una comida modesta, un binario es demasiado difícil de masticar.
- **Pilla-pilla** — con dos o más mascotas en pantalla, marca *Jugar al pilla-pilla entre
  ellas* y una se convierte en "la que la lleva": camina hacia su vecino más cercano mientras
  las demás corren en dirección contraria, y atrapar a alguien le pasa el turno.
- **Reacciona al sonido** — la mascota pulsa con la salida de tus altavoces, o con tu
  **micrófono** para que se mueva mientras hablas. Ambos leen solo el *medidor* de salida — un
  número, no audio. Los picos se suavizan con una ventana RMS y una envolvente de ataque
  rápido/decaimiento lento, de modo que el pulso respira en lugar de parpadear. Con varios
  monitores, cada mascota sigue el punto final de audio que corresponde a su propia pantalla.
- **Temporizador de concentración** — un pomodoro en la misma página, anunciado por la
  mascota: te avisa cuando termina la concentración y cuando el descanso ha terminado.
- **Chat** — la mascota puede responderte a través de Claude cuando `ANTHROPIC_API_KEY` está
  configurado. Desactivado a menos que lo habilites; consulta [Qué sale de la máquina](#qué-sale-de-la-máquina).

**Fondo de pantalla** — reproduce una carpeta de imágenes y animaciones *debajo* de cada
ventana. Cada monitor apunta a su propia carpeta con su propio temporizador, barajada o leída
recursivamente, y puede pulsar con el nivel de los altavoces. Una segunda carpeta puede tomar
el relevo durante las horas de silencio.

**Widgets** — cuatro cosas que se sitúan en el escritorio:

- **Espectro de audio** — barras o un anillo, bandas espaciadas logarítmicamente, suavizadas
  con un seguidor de ataque rápido/decaimiento lento y marcadores de pico que descienden
  lentamente.
- **Reproduciendo ahora** — la pista actual desde los controles multimedia de Windows cuando
  los enlaces opcionales de `winsdk` están instalados; de lo contrario, el nombre de la
  aplicación que realmente está produciendo sonido.
- **Monitor del sistema** — CPU, memoria, disco, batería y rendimiento de red como pequeños
  minigráficos; marca las líneas que quieras. Un promedio oculta un atasco; una línea no. Una
  línea oculta sigue registrando, así que volver a activarla muestra lo que ocurrió mientras
  tanto.
- **Notas adhesivas** — tarjetas editables por encima de cada ventana, que conservan su texto,
  color y posición entre sesiones.

### Trabajo

**Concentración** — dos superposiciones para cuando la pantalla compite con tu trabajo.
*Atenuar las ventanas de fondo* oscurece todo excepto la ventana en la que estás trabajando,
con una intensidad ajustable. *Cubrir una distracción* enmascara una franja de la pantalla: la
barra de tareas, una esquina de notificaciones, un borde, o todo. Ambas dejan pasar los clics,
de modo que lo que cubren sigue funcionando — simplemente deja de atraer tu mirada.

**Cuidado de la pantalla** — para sesiones largas frente a la pantalla:

- **Filtro de color** — siete tonos que van de cálido pasando por ámbar y rosa hasta gris, con
  una intensidad ajustable.
- **Regla de lectura** — atenúa la página y deja una banda brillante que sigue al cursor.
- **Recordatorio de descanso** — la regla 20-20-20, con una superposición de descanso cuando
  se cumple el intervalo.
- **Simulación de visión del color** — protanopía, deuteranopía, tritanopía y acromatopsia con
  una gravedad ajustable, usando el modelo de Machado et al. (2009). A diferencia de las demás
  superposiciones, esta es opaca, porque mostrar lo que otra persona ve significa repintar la
  pantalla en lugar de teñirla.

**Presentaciones** — para demostraciones, clases y grabaciones:

- **Anotación** — dibuja sobre la pantalla con un lápiz, un rotulador o un borrador, con
  deshacer y borrar.
- **Efectos del cursor** — un anillo alrededor del puntero, una onda al hacer clic y un foco
  que atenúa todo lo demás.
- **Visualización de pulsaciones** — muestra lo que acabas de pulsar y qué botón del ratón
  hiciste clic, para que los espectadores puedan seguirte; se desvanece tras un par de
  segundos. Elige dónde se sitúa el panel y qué tamaño tiene el texto, y desactiva los clics
  del ratón por separado.
- **Lupa** — una vista ampliada del área alrededor del cursor.
- **Pizarra** — un lienzo infinito: arrastra para desplazar, desplaza para hacer zoom, guarda
  lo que dibujaste. Los trazos viven en coordenadas del lienzo, de modo que desplazar y hacer
  zoom los deja donde corresponden.
- **Congelar** — fija el fotograma actual de un monitor para que puedas seguir trabajando
  detrás de una imagen fija. `Ctrl+Shift+F7` la libera, lo cual importa porque la imagen
  congelada cubre el botón que lo haría.

**Herramientas** — medición, captura y manejo de ventanas:

- **Selector de color / regla de píxeles / transportador** — haz clic para muestrear o medir;
  el resultado va directamente al portapapeles como `#rrggbb`, `rgb(...)`, `hsl(...)` o una
  propiedad personalizada de CSS.
- **Captura de región** — arrastra para delimitar un área; va al portapapeles, puede guardarse
  en un archivo o **fijarse** encima como una copia flotante con zoom.
- **Grabar área** — graba una región en un GIF animado, con la cámara compuesta en la esquina
  para el aspecto de vídeo de reacción. Limitado tanto por la duración como por el número de
  fotogramas, porque cada fotograma se mantiene en memoria.
- **Cámara** — tu webcam en un círculo, un cuadro redondeado o un rectángulo, mostrada
  localmente y nunca grabada. Cualquier entrada de vídeo funciona, incluidas las capturadoras,
  y la lista de dispositivos se actualiza sin reiniciar, ya que las capturadoras suelen
  conectarse mientras la aplicación ya está en marcha.
- **Cámara virtual** — envía una región, con superposiciones y todo, como una webcam que Zoom,
  Teams o Discord pueden seleccionar como su fuente de vídeo. Necesita el paquete opcional
  `pyvirtualcam` y un controlador de cámara virtual (OBS instala uno); sin alguno de los dos,
  el botón lo indica en lugar de fallar en silencio.
- **Leer texto** — arrastra para delimitar un área y copiar el texto que contiene, traducirlo
  o hacer una pregunta sobre él. Esta función envía la selección fuera de la máquina; consulta
  [Qué sale de la máquina](#qué-sale-de-la-máquina).
- **Fijar una ventana** — mantén la ventana de otro programa por encima, o atenúala, mientras
  trabajas contra ella. Solo se tocan el apilamiento y la opacidad, nunca el contenido de la
  ventana.
- **Réplica de ventana** — una pequeña copia en vivo siempre visible de otra ventana, para que
  puedas ver un renderizado o un chat mientras está enterrado.
- **Distribuciones de ventanas** — guarda dónde se sitúa cada ventana y vuelve a colocarlas más
  tarde. Las ventanas se emparejan por el título; una que no esté en pantalla se omite en lugar
  de adivinarse.

---

## Controlarlo todo a la vez

La página del **Centro de control** alcanza cada superposición de cada página, sea cual sea la
pestaña que la abrió: ocultar, mostrar, cerrar, silenciar, bloquear, restablecer posiciones,
ajustar la opacidad por pasos y aplicar un **nivel de calidad** (alto / equilibrado / ahorro)
que limita la frecuencia de refresco de cada superposición y reduce su resolución de
renderizado. También incorpora un fondo de croma para OBS, un interruptor de *Ocultar de la
captura*, el panel de registro y **Fijar a este escritorio** — las superposiciones se apartan
cuando cambias de escritorio virtual y regresan cuando vuelves. Desfijar recupera lo que había
guardado.

Teclas de acceso rápido globales predeterminadas, todas reasignables desde **Ajustes → Teclas
de acceso rápido**:

| Atajo | Acción |
| --- | --- |
| `Ctrl+Shift+F12` | Cerrar todas las superposiciones |
| `Ctrl+Shift+F11` / `F10` | Ocultar / mostrar todas las superposiciones |
| `Ctrl+Shift+F9` | Silenciar todo |
| `Ctrl+Shift+↑` / `↓` | Subir / bajar la opacidad |
| `Ctrl+Shift+L` | Bloquear o desbloquear (paso de clics vs. arrastrable) |
| `Ctrl+Shift+→` | Página siguiente del panel |
| `Ctrl+Shift+F8` | Mostrar la hoja de atajos en pantalla |
| `Ctrl+Shift+F7` | Congelar / descongelar la pantalla |
| `Ctrl+Shift+F6` / `F5` / `F4` | Reproducir/pausar medios, pista siguiente y anterior |
| `Ctrl+Shift+F3` | Mover la ventana en primer plano al siguiente monitor |
| `F12` | Salir de inmediato (Windows) |

El transporte de medios envía las teclas multimedia del sistema, de modo que llega a cualquier
reproductor que las escuche. Mover una ventana mantiene sus proporciones en lugar de ajustarla
de golpe, que es lo que hace el propio `Win+Shift+Arrow` de Windows.

Las mismas acciones — y nada más allá de ellas — son las que controlan los mandos remotos:

- **Tu teléfono** (Ajustes → Control remoto) — FrontEngine sirve una pequeña página en tu red
  local; abre el enlace en un teléfono y los botones controlan esas acciones.
- **Un controlador MIDI** — pulsa *Aprender*, mueve una perilla o un pad, y asígnalo. Usa el
  winmm integrado de Windows, así que no se necesita ningún paquete adicional. Una perilla se
  dispara una vez que alcanza el máximo en lugar de repetidamente por el camino, y soltar un pad
  no cuenta como una segunda pulsación.

---

## Ajustes preestablecidos y automatización

Los **ajustes preestablecidos** capturan la configuración de cada página a la vez. Guárdalos,
cárgalos, elimínalos, expórtalos e impórtalos desde el menú **Ajustes preestablecidos**, aplica
uno al iniciar, o restaura la sesión anterior automáticamente. Un ajuste preestablecido puede
exportarse como un **paquete** — un zip que lleva los medios a los que hace referencia — para
que se abra en una máquina que no tiene esos archivos.

Cosas que luego deciden por sí solas, todas desde el menú **Ajustes**. La pausa inteligente es la
única que empieza activada; todo lo demás está desactivado hasta que lo enciendes.

| | |
| --- | --- |
| **Reglas** | *"Cuando se cumplan estas condiciones, haz esto."* Combina un día de la semana, una ventana de tiempo y qué aplicación tiene el foco, y luego aplica un ajuste preestablecido, oculta/muestra/cierra las superposiciones, o define la calidad. Una condición en blanco significa "cualquiera", y una regla se ejecuta **una vez** cuando sus condiciones empiezan a cumplirse, en lugar de repetidamente mientras lo hacen. Este es el único lugar donde las condiciones se combinan; las filas de abajo conocen cada una un solo tipo. |
| **Pausa inteligente** | Retira las superposiciones mientras se ejecuta una aplicación en pantalla completa, mientras la máquina está con batería, o mientras una aplicación concreta tiene el foco. *(Activada por defecto, para la regla de pantalla completa.)* |
| **Perfiles de aplicación** | Aplica un ajuste preestablecido cuando cambias a una aplicación determinada. |
| **Programación de ajustes preestablecidos** | Aplica un ajuste preestablecido en los días de la semana elegidos a una hora fijada. |
| **Programación de temas** | Alterna entre un tema de día y uno de noche según el reloj. |
| **Modo señalización** | Rota una lista de ajustes preestablecidos con un temporizador y la ventana principal retirada, para una máquina que se deja funcionando como pantalla. |
| **Salvapantallas** | Tras un umbral de inactividad, muestra el vídeo / imagen / GIF / partículas / página web que elegiste, y lo retira cuando vuelves. |
| **Recordatorios** | Cada N minutos, o una vez al día a una hora fijada, mostrados como una notificación emergente que se cierra sola. |
| **Mantener activo** | Impide que la pantalla se suspenda mientras hay superposiciones activas. |
| **Iniciar con el sistema** | Se ejecuta al iniciar sesión. |
| **Tiempo de pantalla** | Qué aplicaciones tuvieron el foco y durante cuánto tiempo, con un desglose diario y un resumen de siete días. Se pausa mientras estás lejos del teclado, conserva 60 días como máximo, y borrarlo elimina el propio archivo. |
| **Historial del portapapeles** | Busca lo que copiaste y fija las frases que reutilizas. Los portapapeles habitualmente contienen contraseñas, así que esto se mantiene **solo en memoria** a menos que marques por separado "mantener entre sesiones". |

---

## Idiomas

Siete: English, 繁體中文, 简体中文, Deutsch, Русский, Français, Italiano.

Elige uno del menú **Idioma** y la interfaz cambia **de inmediato** — sin reiniciar. Lo que
tuvieras abierto permanece abierto: las superposiciones siguen funcionando, y los ajustes de
cada página se dejan exactamente como estaban. En una instalación de Steam, el primer inicio
sigue el idioma del propio cliente de Steam.

---

## Notas de privacidad y de plataforma

### Qué sale de la máquina

Todo en FrontEngine es local a menos que esté en esta lista. Hay cuatro excepciones, todas
opcionales:

| Función | A dónde va | Salvaguarda |
| --- | --- | --- |
| **Leer texto** (Herramientas) | La región seleccionada se envía a la API de Anthropic | Pregunta una vez antes del primer envío y recuerda la respuesta; el consentimiento puede retirarse desde la ventana de resultados. Usa tu propia `ANTHROPIC_API_KEY`, leída del entorno y nunca escrita en un archivo de configuración. No se envía nada sin ambas. |
| **Chat de la mascota** | Tu mensaje va a la API de Anthropic | La misma clave, la misma regla; desactivado por defecto. |
| **Tiempo meteorológico** (fuente de texto) | Las coordenadas van a Open-Meteo | Sin clave, sin cuenta, sin datos identificativos; solo lo que escribiste como ubicación. |
| **Remoto por teléfono** | Sirve una página en tu red local | Desactivado por defecto. El enlace lleva un token que se regenera en cada arranque, así que un enlace antiguo deja de funcionar, y la página solo puede solicitar la lista fija de acciones. Es HTTP simple: alguien más en la misma red podría leer el token y pulsar los mismos botones — una molestia más que una brecha, dado lo que hacen esos botones, pero déjalo desactivado en redes en las que no confíes. |

Las funciones de audio leen solo un **medidor** de salida — un único número — excepto el
espectro, que necesita muestras reales para calcular frecuencias y por eso captura el flujo de
salida del sistema. Esas muestras se analizan en memoria, nunca se escriben en disco ni se
envían a ninguna parte, y la captura se detiene en el momento en que detienes el espectro.

Los **plugins** son Python y se ejecutan con los mismos privilegios que FrontEngine — no
pueden aislarse en un entorno controlado. La carga está desactivada por defecto (Ajustes →
Cargar plugins), cada carga se registra, y un plugin defectuoso se omite en lugar de detener
la aplicación. Instala solo plugins en los que confíes.

### Privacidad al compartir pantalla

Tus superposiciones son para ti, no para las personas con las que compartes. Desde **Ajustes →
Privacidad al compartir pantalla**, FrontEngine puede sacarlas de la captura mientras una
aplicación de reuniones está abierta:

- **Permanecen en tu propia pantalla.** Solo la copia capturada queda en blanco — esto usa el
  `WDA_EXCLUDEFROMCAPTURE` de Windows, una marca a nivel de sistema operativo que las
  aplicaciones de conferencias y los grabadores respetan.
- **Las máscaras son la excepción.** Una máscara de distracción existe para cubrir algo, así
  que deliberadamente permanece visible en la captura.
- **El desencadenante es tu lista.** Windows no tiene una API fiable de "¿me están
  capturando?", así que vigila los títulos de ventana que nombras — lo cual también atrapa una
  reunión celebrada en una pestaña del navegador, donde el ejecutable es simplemente el
  navegador.

También hay un botón manual de *Ocultar de la captura* en el centro de control.

> Esto es privacidad, no seguridad: derrota la vía de captura ordinaria, y nunca oculta nada de
> la persona sentada al escritorio.

### Compatibilidad de plataformas

Todo lo que no figura aquí funciona en las tres plataformas.

| Función | Windows | macOS | Linux |
| --- | :---: | :---: | :---: |
| Superposiciones, mascota, fondo de pantalla, presentaciones, cuidado de la pantalla, captura, grabación | ✅ | ✅ | ✅ |
| Reacción al audio, espectro, sincronización labial (WASAPI) | ✅ | — | — |
| Reproduciendo ahora (controles multimedia) | ✅ | — | — |
| Fijar / atenuar otra ventana, distribuciones de ventanas, réplica en vivo | ✅ | — | — |
| Ocultar superposiciones de la captura de pantalla | ✅ | — | — |
| Control MIDI (winmm) | ✅ | — | — |
| Teclas de transporte de medios | ✅ | — | — |
| Fijar superposiciones a un escritorio virtual | ✅ | — | — |
| Mover una ventana al siguiente monitor | ✅ | — | — |
| Salida de emergencia `F12` | ✅ | — | — |
| Atenuar el fondo alrededor de la ventana *activa* | ✅ | pantalla completa | pantalla completa |
| Mascota posándose sobre otras ventanas | ✅ | — | con `wmctrl` |

Donde una función no puede funcionar, el botón lo indica en lugar de fallar en silencio.

---

## Ampliación

- **Steam Workshop** — los elementos a los que te suscribes se recogen de la propia carpeta
  `steamapps/workshop/content` de Steam: los ajustes preestablecidos se importan y los packs de
  mascota se listan con sus rutas, desde **Ajustes preestablecidos → Importar contenido del
  Workshop**. Publicar en el Workshop necesita el SDK de Steamworks y no está integrado.
- **Plugins** — una carpeta `plugins/` puede añadir sus propias pestañas, ya sea mediante una
  asignación `FRONTENGINE_TABS = {"name": WidgetClass}` o un gancho `register(registry)`. Lee
  antes la nota de confianza anterior.

---

## Desarrollo

```bash
pip install -r dev_requirements.txt
pip install -e .

python -m pytest tests/ -q          # the whole suite, headless (Qt offscreen)
```

La comprobación estática usa pyflakes (en `dev_requirements.txt`), y un árbol limpio no imprime
absolutamente nada:

```bash
python -m pyflakes frontengine/ exe/ tests/
```

El conjunto de pruebas se ejecuta enteramente fuera de pantalla y no necesita pantalla, tarjeta
de sonido ni cámara; cualquier cosa que toque el mundo exterior toma una fuente inyectable para
poder probarse con una falsa.

- **Arquitectura** — [`architecture_explore.md`](../architecture_explore.md) mapea cada módulo,
  la estratificación, el contrato de superposición y los puntos de extensión. Léelo antes de
  añadir una página o una superposición: varias cosas (el registro del centro de control, siete
  diccionarios de idioma, siete árboles de documentación) tienen que actualizarse juntas, y las
  pruebas lo exigen.
- **Contribuir** — consulta [`CONTRIBUTING.md`](../CONTRIBUTING.md). Una función por pull
  request, todas las comprobaciones de CI en verde.
- **Compilar el ejecutable de Windows** — `python exe/build_exe.py` (Nuitka; añade `--onefile`
  para un solo archivo).
- **Documentación** — fuentes de Sphinx en `docs/`, publicadas en
  [Read the Docs](https://frontengine.readthedocs.io/en/latest/) en los siete idiomas.

---

## Integración continua y publicaciones

El trabajo fluye `feature → dev → main`, y solo el último paso publica:

```
feat/xyz  ──PR──►  dev  ──PR──►  main
                    │              │
              CI, no release   CI + release
```

| Flujo de trabajo | Desencadenante | Propósito |
| --- | --- | --- |
| `CI` (`ci.yml`) | Push / PR a `main` o `dev`, activación manual, o llamado por `Nightly` | Compila, ejecuta las pruebas unitarias, y luego construye un wheel a partir de *ese checkout*, lo instala e inicia la aplicación — en Python 3.10 / 3.11 / 3.12, Windows |
| `Nightly` (`nightly.yml`) | Cron diario, activación manual | Llama a `CI`. La programación vive aquí a propósito: GitHub desactiva los flujos de trabajo que contienen un cron tras ~60 días de inactividad, y eso, de lo contrario, se llevaría por delante las comprobaciones de PR |
| `Release` (`release.yml`) | Un pull request **desde `dev`** se fusiona en `main`, o activación manual | Incrementa la versión, la vuelve a confirmar con `[skip ci]`, intercambia `stable.toml` → `pyproject.toml`, construye sdist + wheel, sube a PyPI como `frontengine`, crea una release de GitHub etiquetada como `v<version>`, y hace fast-forward de `dev` |

La publicación ocurre **solo cuando `dev` se fusiona en `main`**. Las funciones aterrizan en
`dev` sin acuñar una versión, y una publicación es un pull request `dev → main` deliberado. Un
PR de función dirigido a `main` por error igualmente se fusiona pero no publica — la dirección
del fallo es una publicación faltante, no una no deseada.

El segmento de parche se incrementa automáticamente; para una publicación menor o mayor, ejecuta
*Actions → Release → Run workflow* y elige el segmento. Esa vía también vuelve a ejecutar una
publicación fallida sin necesitar una nueva fusión.

Las versiones viven en dos archivos: `pyproject.toml` es el paquete de desarrollo
(`frontengine_dev`) y `stable.toml` es el publicado (`frontengine`).

Se requiere un secreto de repositorio: `PYPI_API_TOKEN`, un token de PyPI con alcance al
proyecto `frontengine`. El flujo de trabajo usa `__token__` como nombre de usuario de twine, así
que solo hace falta almacenar el propio token.

---

## Licencia

Consulta [`LICENSE`](../LICENSE). Las expectativas de la comunidad están en
[`Contributor_Covenant_Code_of_Conduct.md`](../Contributor_Covenant_Code_of_Conduct.md).
