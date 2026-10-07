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
> completo** desde cualquier lugar (Windows; macOS necesita permiso de Accesibilidad — consulta *Ayuda → Cómo forzar el cierre*).

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
- **Grabar área** — Grabación: selecciona un área y el GIF o AVI de destino antes de iniciar la captura. Cancelar no empieza a grabar. Un hilo en segundo plano escribe los fotogramas de forma incremental; la cola admite tres fotogramas y 64 MiB como máximo. Un fotograma demasiado grande se rechaza. Con la cola llena se omiten capturas conservando el tiempo transcurrido en la reproducción. Se mantienen frecuencia, límites de duración y fotogramas e inserto de cámara. Detener finaliza de forma asíncrona; el archivo sustituye el destino atómicamente solo tras el éxito. Cancelaciones y errores eliminan el temporal y preservan el destino existente.
- **Cámara** — tu webcam en un círculo, un cuadro redondeado o un rectángulo, mostrada
  localmente y nunca grabada. Cualquier entrada de vídeo funciona, incluidas las capturadoras,
  y la lista de dispositivos se actualiza sin reiniciar, ya que las capturadoras suelen
  conectarse mientras la aplicación ya está en marcha.
- **Cámara virtual** — envía una región, con superposiciones y todo, como una webcam que Zoom,
  Teams o Discord pueden seleccionar como su fuente de vídeo. Necesita el paquete opcional
  `pyvirtualcam` y un controlador de cámara virtual (OBS instala uno); sin alguno de los dos,
  el botón lo indica en lugar de fallar en silencio.
- **Leer texto** — Texto en pantalla: Herramientas → Leer texto usa primero OCR local: Windows.Media.Ocr en Windows, Vision en macOS o Tesseract instalado con sus datos de idiomas. La extracción local no necesita consentimiento para la nube ni ANTHROPIC_API_KEY; un resultado vacío correcto no sube una captura. Traducciones y preguntas solo pueden enviar texto reconocido a Anthropic con consentimiento separado para texto y tu clave. La captura como alternativa tras un fallo local requiere consentimiento propio para imágenes y la clave. El resultado muestra el motor y errores; allí puedes retirar el consentimiento.
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
| `F12` | Salir de inmediato (Windows / macOS*) |

El transporte de medios envía las teclas multimedia del sistema, de modo que llega a cualquier
reproductor que las escuche. Mover una ventana mantiene sus proporciones en lugar de ajustarla
de golpe, que es lo que hace el propio `Win+Shift+Arrow` de Windows.

Las mismas acciones — y nada más allá de ellas — son las que controlan los mandos remotos:

- **Tu teléfono** (Ajustes → Control remoto) — FrontEngine sirve una pequeña página en tu red
  local; abre el enlace en un teléfono y los botones controlan esas acciones.
- **Un controlador MIDI** — Pulsa Learn, mueve una perilla o pad y asígnalo. Windows usa winmm integrado; macOS usa CoreMIDI con el extra macos. La perilla se activa una vez al llegar arriba y soltar un pad no cuenta como otra pulsación.

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
| **Leer texto** (Herramientas) | Anthropic API | Texto en pantalla: Herramientas → Leer texto usa primero OCR local: Windows.Media.Ocr en Windows, Vision en macOS o Tesseract instalado con sus datos de idiomas. La extracción local no necesita consentimiento para la nube ni ANTHROPIC_API_KEY; un resultado vacío correcto no sube una captura. Traducciones y preguntas solo pueden enviar texto reconocido a Anthropic con consentimiento separado para texto y tu clave. La captura como alternativa tras un fallo local requiere consentimiento propio para imágenes y la clave. El resultado muestra el motor y errores; allí puedes retirar el consentimiento. |
| **Chat de la mascota** | Tu mensaje va a la API de Anthropic | La misma clave, la misma regla; desactivado por defecto. |
| **Tiempo meteorológico** (fuente de texto) | Las coordenadas van a Open-Meteo | Sin clave, sin cuenta, sin datos identificativos; solo lo que escribiste como ubicación. |
| **Remoto por teléfono** | HTTPS | Control por teléfono: Configuración → Control remoto usa solo HTTPS, un token nuevo en cada inicio y una lista fija de acciones. El teléfono no confía automáticamente en el certificado autofirmado. Exporta el certificado público y compara la huella SHA-256 mostrada antes de importarlo o confiar en él desde los ajustes del teléfono/navegador. La clave privada permanece en la carpeta de datos del usuario. Cambios de IP, caducidad o regeneración pueden exigir confiar en un nuevo certificado. Un fallo de inicio TLS no vuelve a HTTP. |

Las funciones de audio leen solo un **medidor** de salida — un único número — excepto el
espectro, que necesita muestras reales para calcular frecuencias y por eso captura el flujo de
salida del sistema. Esas muestras se analizan en memoria, nunca se escriben en disco ni se
envían a ninguna parte, y la captura se detiene en el momento en que detienes el espectro.

Plugins: activar la carga no autoriza un plugin. plugin.json o un sidecar para un solo archivo declara versión, identidad, entrada y capacidades; se comprueba la aprobación antes del import Python y se vincula al resumen del contenido. Cambios de código o declaración exigen aprobar de nuevo; plugins antiguos requieren confianza plena explícita. Configuración permite revocar aprobaciones; reinicia para descargar código activo. Los plugins Python conservan todos los privilegios de la aplicación: declaración y consentimiento no son un sandbox del sistema operativo.

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
| Superposiciones e interfaz comunes | ✅ | ✅ | ✅ |
| Audio del sistema, espectro y micrófono | ✅ | backend* | — |
| Metadatos de reproducción actual | ✅ | — | — |
| Geometría, disposición y traslado de ventanas | ✅ | backend* | — |
| Copia de ventana en directo | ✅ | backend* | — |
| Ventanas ajenas: primer plano / opacidad | ✅ | — | — |
| Excluir superposiciones de capturas | ✅ | — | — |
| Control MIDI | ✅ | backend* | — |
| Teclas multimedia | ✅ | backend* | — |
| Escritorio virtual / selección de Space | ✅ | — | — |
| Salida de emergencia F12 | ✅ | backend* | — |
| Mascota sobre otras ventanas | ✅ | backend* | wmctrl |

* Las entradas macOS «backend» requieren el extra macos, macOS 13+ y los permisos correspondientes. Describen rutas de frameworks públicos implementadas, no validación nativa desde este equipo Windows; consulta las notas siguientes.

Donde una función no puede funcionar, el botón lo indica en lugar de fallar en silencio.

---

## Ejecución, privacidad e interoperabilidad

Grabación: selecciona un área y el GIF o AVI de destino antes de iniciar la captura. Cancelar no empieza a grabar. Un hilo en segundo plano escribe los fotogramas de forma incremental; la cola admite tres fotogramas y 64 MiB como máximo. Un fotograma demasiado grande se rechaza. Con la cola llena se omiten capturas conservando el tiempo transcurrido en la reproducción. Se mantienen frecuencia, límites de duración y fotogramas e inserto de cámara. Detener finaliza de forma asíncrona; el archivo sustituye el destino atómicamente solo tras el éxito. Cancelaciones y errores eliminan el temporal y preservan el destino existente.

Control por teléfono: Configuración → Control remoto usa solo HTTPS, un token nuevo en cada inicio y una lista fija de acciones. El teléfono no confía automáticamente en el certificado autofirmado. Exporta el certificado público y compara la huella SHA-256 mostrada antes de importarlo o confiar en él desde los ajustes del teléfono/navegador. La clave privada permanece en la carpeta de datos del usuario. Cambios de IP, caducidad o regeneración pueden exigir confiar en un nuevo certificado. Un fallo de inicio TLS no vuelve a HTTP.

Texto en pantalla: Herramientas → Leer texto usa primero OCR local: Windows.Media.Ocr en Windows, Vision en macOS o Tesseract instalado con sus datos de idiomas. La extracción local no necesita consentimiento para la nube ni ANTHROPIC_API_KEY; un resultado vacío correcto no sube una captura. Traducciones y preguntas solo pueden enviar texto reconocido a Anthropic con consentimiento separado para texto y tu clave. La captura como alternativa tras un fallo local requiere consentimiento propio para imágenes y la clave. El resultado muestra el motor y errores; allí puedes retirar el consentimiento.

Mascotas puppet: instala el extra opcional puppet y un runtime Imervue disponible, luego elige o arrastra un archivo original Imervue .puppet v1 a la página Mascota. Los paquetes de imágenes y sprites existentes siguen funcionando. Los puppets usan lienzo, movimientos y expresiones de Imervue, admiten clonado/cierre y participan en controles de superposición y ajustes preestablecidos. Un .petscript.json opcional usa el motor de scripts existente de Imervue; los paquetes FrontEngine pet.json no son archivos puppet. Versiones desconocidas, rutas peligrosas y recursos inválidos se rechazan antes de cargar el runtime.

Escenas: la página Escena acepta el antiguo mapa JSON de entradas, documentos versionados frontengine.scene y paquetes portables .fescene. PUPPET contiene posición, tamaño, opacidad, parámetros numéricos finitos y movimiento, expresión o script opcionales. Las rutas JSON se resuelven respecto al archivo de escena. .fescene incluye medios referenciados, el .puppet original y .petscript.json opcional para trasladarse entre equipos. La importación comprueba rutas, enlaces simbólicos, versiones y límites de extracción. Una escena FrontEngine sigue siendo un paquete de escena; .puppet sigue siendo un personaje Imervue.

macOS: el extra macos usa macOS 13+ y frameworks públicos PyObjC. Los motores proporcionan ScreenCaptureKit para pantalla/ventanas y audio del sistema, micrófono, geometría Quartz, disposición/movimiento mediante Accesibilidad, CoreMIDI, teclas multimedia y salida F12. Grabación de pantalla, Accesibilidad y Micrófono se comprueban por separado; usa Ajustes del Sistema → Privacidad y seguridad y reinicia cuando se indique. Opacidad/primer plano forzado de ventanas ajenas, selección de Spaces y exclusión de capturas ajenas siguen sin estar disponibles. Permisos nativos, hardware y rendimiento macOS no se han verificado desde este equipo Windows. Configuración → Permisos y capacidades de macOS muestra cada función como disponible, no disponible o no compatible, con el motivo de permisos o instalación.

Plugins: activar la carga no autoriza un plugin. plugin.json o un sidecar para un solo archivo declara versión, identidad, entrada y capacidades; se comprueba la aprobación antes del import Python y se vincula al resumen del contenido. Cambios de código o declaración exigen aprobar de nuevo; plugins antiguos requieren confianza plena explícita. Configuración permite revocar aprobaciones; reinicia para descargar código activo. Los plugins Python conservan todos los privilegios de la aplicación: declaración y consentimiento no son un sandbox del sistema operativo.

Renderizado: Configuración → Renderizado de superposiciones ofrece Auto, GPU o Software y muestra el motor real. El compositor GPU usa texturas OpenGL, shaders y framebuffers para orden, transformaciones, opacidad y recorte; un fallo de inicialización vuelve al software mostrando el motivo. QPainter puede seguir rasterizando en CPU antes de subir texturas; widgets web/vídeo/nativos pueden usar ventanas separadas. Captura y grabación pueden leer fotogramas GPU a CPU. Esto no promete captura sin copias ni mejoras de velocidad medidas.

Instala las funciones opcionales con los comandos siguientes. Las proyecciones WinRT del OCR se incluyen en la instalación normal de FrontEngine en Windows; instala los idiomas de reconocimiento de Windows. Tesseract requiere su ejecutable y datos de idiomas por separado. El extra puppet añade Imervue>=1.0.90; macos añade frameworks PyObjC para macOS 13+. Los formatos y ejemplos están en docs/formats/.

```bash
pip install "frontengine[puppet]"
pip install "frontengine[macos]"
```

[.puppet / pet.json / .petscript.json / .fescene](../docs/formats/interoperability.md)

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

Los manifiestos de Workshop tienen versión y se validan antes de usarlos. Los JSON de metadatos desconocidos no se consideran ajustes predefinidos. Los paquetes rechazan rutas de archivo inseguras, límites de recursos excedidos y nombres de medios duplicados.

Preajustes → Gestionar Workshop abre el gestor de Steam; Escena y Mascota también tienen accesos. Windows x64 requiere Steam conectado para App 2793470 y steam_api64.dll. Publique escenas .fescene/JSON, ZIP de preajustes o carpetas de mascotas sprite con vista previa PNG/JPEG menor de 1 MB. Los elementos nuevos son privados; las actualizaciones verifican al propietario. Las cargas muestran progreso y acuerdo, guardan ID para reintentos y continúan al ocultar la ventana. Compruebe en Steam los resultados interrumpidos. Las suscripciones se validan y copian a carpetas de versiones separadas; los conflictos permiten elegir la versión descargada o local. Cargar rellena la página correspondiente; inicie allí la reproducción. Los preajustes necesitan un nombre nuevo. Se mantiene la importación sin conexión. Para Steam añada --steam-runtime RUTA_DLL a exe/build_exe.py; la DLL acompaña al ejecutable, también con --onefile. Se excluyen el SDK y steam_appid.txt de desarrollo.

Windows incluye winrt-Windows.Media.Control para mostrar canción y artista mediante SMTC en el widget de reproducción; winsdk antiguo sigue como alternativa. Sin sesión multimedia el resultado está vacío; se conserva la alternativa del nombre de la aplicación de audio.

La compilación del ejecutable comprueba dependencias y versiones antes de compilar; instale primero requirements.txt en ese entorno.

Escena → Editor visual ofrece lista y vista previa de capas de imagen/GIF/texto, arrastre grupal, tamaño desde la esquina, posición/tamaño/escala/rotación/orden/opacidad, alineación, bloqueo, visibilidad, duplicado y 100 pasos de deshacer/rehacer (Ctrl+Z/Ctrl+Y). Exporte .fescene directamente; Script permite editar y aplicar JSON. La reproducción restaura tamaño, escala, rotación y visibilidad explícitos. El JSON externo inicia un historial nuevo y conserva los campos existentes.

Abre Comandos en el menú o pulsa Ctrl+K / Ctrl+Mayús+P en FrontEngine. Busca en el idioma actual, etiquetas inglesas o nombres estables; las flechas seleccionan y Intro ejecuta. Incluye navegación, captura, notas, filtro, Workshop y acciones globales. Preajuste/calidad aceptan un valor. Favoritos y últimos 20 comandos persisten; argumentos y búsquedas no se guardan.

Texto → TXT / JSON / CSV local muestra UTF-8 con campo e intervalo de 1–3600 segundos. JSON: /clave/índice (p. ej. /build/tasks); CSV: cabeceras únicas, columna por líneas. Campo vacío: archivo completo. Lectura en segundo plano, una tarea por fuente, límite 1 MiB y 65.536 caracteres. Errores de archivo/campo, formato, acceso y tamaño son explícitos; las correcciones recuperan el resultado. Los preajustes guardan archivo/campo/intervalo. Las escenas portables copian el archivo: compartir el paquete comparte esa instantánea.

Herramientas → Paleta de colores recoge clics consecutivos al activar la colección. Nombra/agrupa, edita hex exactos, busca, copia y elimina; reutiliza muestras recientes. Hasta 512 colores y 50 muestras distintas se guardan localmente. Nombres únicos por grupo, sin distinguir mayúsculas; duplicados rechazados. CSS/JSON conservan RGB; colisiones CSS llevan números. Exportación atómica. Comandos también abre la paleta.

Preajustes → Versiones de preajustes conserva hasta 50 instantáneas distintas por preajuste entre reinicios. Al guardar registra las configuraciones anterior y nueva sin duplicados. Seleccionar una versión muestra diferencias de campos frente a los ajustes actuales de las páginas. La vista previa aplica esa configuración a los controles; Cancelar, Escape o cerrar restaura los ajustes originales. Restaurar aplica y guarda la versión, revirtiendo los ajustes de las páginas si falla la aplicación o el guardado. Las instantáneas contienen rutas de medios, sin copiarlos; la vista previa no abre superposiciones. Los preajustes JSON/ZIP existentes siguen siendo compatibles. El historial en presets/.versions permanece tras eliminar un preajuste para reutilizar su nombre.

Mascota → Identidades guarda UUID, nombre, ánimo, saciedad y afecto independientes para cada sprite o puppet. Antes de crearla elija una identidad guardada para continuar tras reiniciar; Nueva mascota empieza de nuevo. Solo la primera identidad migra una vez los antiguos valores compartidos. Clonar copia los valores actuales a una identidad nueva; alimentar no cambia otras mascotas. Renombre, actualice, exporte o importe guardados JSON individuales; importar siempre crea una identidad nueva. Una identidad solo puede estar activa una vez. Los guardados no incluyen imágenes, scripts ni chats; los preajustes portátiles excluyen IDs locales. Hasta 256 identidades se almacenan en ajustes; los cambios de sprites se guardan tras una breve espera y al cerrar. Alimentar un puppet solo modifica valores guardados, no movimientos ni tamaño de Imervue.

Imagen → Comparar imágenes muestra dos referencias con zoom/desplazamiento compartidos: lado a lado, superposición transparente, separador deslizante o diferencia absoluta RGB. Alinee arriba a la izquierda o al centro sin escalar, o ajuste B dentro de A proporcionalmente. La rueda amplía ambas; el deslizador controla opacidad de B o separador. Transparencia y márgenes se comparan sobre blanco; negro significa RGB iguales. Solo se usa el primer fotograma animado. Decodificación, alineación y cálculo se ejecutan en segundo plano con una solicitud cada vez y solo se aplica la selección más reciente; opacidad/separador reutilizan imágenes. Límites: 64 MiB por archivo, 8.192 píxeles por lado y 16.777.216 por imagen/lienzo. Un fallo conserva el par anterior; cerrar libera imágenes e ignora resultados tardíos.

Ajustes → Reglas añade prioridad (-1000…1000), espera (0…86400 segundos enteros), vista previa de condiciones e historial de sesión. Las reglas activadas van de prioridad baja a alta; empates mantienen el orden de la tabla. La espera usa un reloj monotónico: consume las transiciones bloqueadas y no ejecuta al vencer si las condiciones siguen verdaderas. La vista previa inspecciona filas sin guardar, sin acciones ni transiciones consumidas. Los últimos 200 registros conservan condiciones, contexto y resultados enviado/ejecutado/fallo/espera solo en memoria. Las filas nombradas inválidas impiden guardar. Hasta 200 reglas tienen identidades distintas incluso con nombres iguales; las condiciones no mostradas se conservan. Los fallos declarados por las acciones se registran y no detienen reglas posteriores.

Las reglas cargan, reproducen o detienen escenas y muestran, ocultan, mueven o cambian la opacidad de capas nombradas. Seleccione la fila y Elegir escena / capa para buscar JSON, .fescene o .puppet, elegir pantalla principal/todas/índice y una capa del editor. Una ruta vacía reproduce la escena actual. Los archivos se leen en segundo plano; un candidato fallido conserva la reproducción existente. La última solicitud reemplaza las pendientes; las acciones de capa posteriores esperan y fallan con ella. Se rechazan capas bloqueadas o ausentes. Los cambios admiten deshacer y actualizan la reproducción; opacidad 0–100, posición ±100000. Detener cancela solicitudes y cierra la reproducción; los recursos del editor quedan hasta reemplazar o cerrar la aplicación. El historial refleja el resultado asíncrono real. Paleta de comandos: ruta o {"path":"scene.fescene","screen":"primary"}, clave para mostrar/ocultar, {"layer":"title","opacity":50} o {"layer":"title","x":20,"y":30}.

Escena → Script → Plantillas de escena (también en la paleta de comandos) ofrece Escritorio de trabajo, Enseñanza y Concentración con texto traducido editable. Previsualice y elija pantalla principal o número antes de Aplicar y reproducir; las proporciones se adaptan al tamaño lógico disponible. Se incluyen todos los recursos; los ausentes se indican por capa/campo/ruta y bloquean la aplicación. La transacción de escena reemplaza editor y reproducción; la preparación fallida conserva la escena anterior. Modifique el texto, añada medios y exporte JSON o .fescene portátil. Cerrar la biblioteca cancela solo su propia aplicación pendiente. Concentración incluye recordatorios editables; programación y temporizadores siguen siendo herramientas independientes.

Escena → Editor visual añade vídeo, web, Puppet y audio a imagen/GIF/texto. Active las vistas en vivo explícitamente: hasta ocho fuentes, silenciadas hasta Escuchar, pausadas al ocultar y liberadas al desactivar o cerrar. Fotogramas limitados a 1280 píxeles por lado; errores visibles. Las escenas con capas nombradas componen vídeo, superficie propia web y fotogramas Puppet fuera de pantalla Imervue con todas las capas visuales en orden z; audio invisible. Doble clic en web/Puppet durante reproducción o Interactuar en el editor abre la misma ventana nativa. Puppet requiere OpenGL nativo y runtime opcional; la vista no ejecuta scripts y las mascotas de escena usan estado temporal. Ventanas web/vídeo/Puppet independientes disponibles. JSON/.fescene conserva tipos y referencias compatibles.

Herramientas → Grabar área ofrece GIF o AVI silencioso (Motion JPEG), 1–20 fps, Pausa/Reanudar y Cancelar. El estado muestra segundos efectivos, fotogramas aceptados y descartados. Las pausas no cuentan en reproducción ni límite; se puede detener en pausa. AVI: una hora, 72.000 fotogramas y 2 GiB; GIF: 120 segundos/600 fotogramas. Ambos usan cola de tres fotogramas/64 MiB y salida atómica. AVI conserva un JPEG e indexa en disco; intervalos descartados repiten la última imagen. Fallos de codificación, tamaño o disco y cancelación preservan el destino existente. Sin audio.

Escena → Editor visual → Línea de animación edita x/y/opacidad de una capa desbloqueada, con inicio de fundido o deslizamiento. Tiempos únicos crecientes: 0–3600 segundos, 128 claves por capa; opacidad 0–100, posición ±100000, linear/smooth. Celdas vacías mantienen el canal. Aplicar permite deshacer; JSON/.fescene conserva pistas. Explore, reproduzca, pause, reanude o repita sin guardar posiciones temporales; restablezca antes de editar. Reproducción: controles separados y reloj monotónico compartido entre pantallas. Ocultar pausa el tiempo; pausa explícita persiste al mostrar. Medios siguen la pausa; repetir controla pistas. Acciones de escena funden un fotograma anterior 0,5 segundos, liberan motores antiguos y empiezan en cero. Escenas antiguas compatibles.

Escena → Salida independiente muestra la escena del editor a 640×480, 1280×720 o 1920×1080 píxeles, independiente de posición, oclusión y DPI. Vista previa sin cámara; envío explícito requiere pyvirtualcam y controlador compatible. Abrir/enviar/cerrar en un trabajador con último RGB pendiente; dispositivos lentos omiten intermedios. Sin audio. IMAGE/GIF/TEXT y VIDEO/WEB/PUPPET nativos siguen orden; SOUND invisible. Puppet requiere runtime opcional y OpenGL nativo; errores visibles. Hasta 256 capas, ocho fuentes nativas y 16 megapíxeles de ráster total. Detener, Escape, cerrar o editar libera motores y solicita cierre de cámara; reinicie tras editar. Lectores cerrados antes de liberar paquetes.

Mascota → Editor de sprites asigna walk/idle/sleep/climb/fall/drag, muestra tamaño y velocidad y exporta una carpeta portátil con pet.json. Requiere una acción; las ausentes se indican y usan el recurso alternativo del cargador. PNG/JPEG/GIF/WebP: 64 MiB y 16 megapíxeles por archivo, 256 MiB en total. Importación/exportación en segundo plano cancelable, sin sobrescribir carpetas. Carpetas trasladables, seleccionables en Mascota y compartibles como packs Workshop. Solo conserva sprites elegidos, nombre, tamaño y velocidad; no sonidos, scripts ni diálogos. Imervue .puppet usa un formato de creación aparte. Cerrar/Escape libera animaciones y cancela operaciones.

Herramientas → Editar última captura abre una copia con recorte, flechas, números, texto y ocultación negra opaca. Arrastre sobre vista escalada; coordenadas/salida siguen píxeles físicos. Deshacer/reiniciar y original de solo lectura. Copiar/guardar PNG/fijar usan el mismo resultado plano incluso viendo el original. Ocultación pintada al final; PNG sin original ni capas ocultas. Captura original separada en memoria. Guardado PNG atómico. Límites: 16 megapíxeles, 1000 marcas, 2000 caracteres/texto, 20 estados de deshacer. Cerrar/reemplazar libera documento.

Presentación → Pizarra añade páginas editables independientes, dibujo/selección, multiselección Mayús, mover/borrar trazos y 20 estados de deshacer totales. Botón central desplaza y rueda amplía; selección/movimiento en coordenadas de lienzo, vista por página. .fewhiteboard JSON versionado guarda vectores/vistas para reeditar. Un trabajador valida/lee/escribe; errores conservan pizarra/archivo. PNG solo de página elegida, sin controles/selección/transformaciones y con margen completo del lápiz. Límites: 50 páginas, 2000 trazos/página, 100000 puntos, ocho MiB JSON; PNG 8192 píxeles/lado y 16 megapíxeles. Cerrar/Escape cancela escritura e ignora lecturas tardías.

Ajustes → Historial de imágenes se activa aparte y está apagado. Abrir no vigila/lee portapapeles. Aplicar activa grabación y SQLite local opcional. 10–200 imágenes, 8–128 MiB PNG; favoritos protegidos pero cuentan, si llenan capacidad rechaza nuevos. Imagen hasta 16 MP/ocho MiB codificada. Un trabajador comprime/miniaturiza/escribe, solo última imagen pendiente y resultados agrupados; omite intermedias si lento. Favoritos/borrar/limpiar, copiar original, fijar y tablero en memoria. Limpiar incluye favoritos/libera páginas; desactivar guardado elimina base manteniendo memoria. clipboard-images.sqlite3 junto ajustes, base hasta 132 MiB más posibles diarios temporales. Sin subidas/OCR automático. Salir desconecta y solicita limpieza asíncrona.

Herramientas → OCR actualizado muestra texto junto a región fija. Inicialmente manual/local; auto explícito 5–60 segundos, copia texto visible/histórico y veinte resultados únicos en memoria. Igual/vacío no duplica. Cuatro ventanas, un trabajo cada una, captura 16 MP/ocho MiB codificada, 20000 caracteres; trabajos lentos omiten repeticiones. Local nunca usa nube aun con consentimiento global. Nube explícita usa consentimiento de capturas/credenciales ScreenTextService y revisión aparte, sin diálogo automático/traducción/subida de texto. Cada actualización puede enviar región. Rechaza solapamiento para evitar realimentación. Windows/X11: Qt local pantalla; Mac: captura nativa asíncrona única, flujo detenido tras imagen. Ocultar detiene captura/timer; cerrar/Escape libera fuentes/historia e ignora resultados tardíos sin esperar. API ya enviada puede terminar. Limpieza colectiva incluye ventanas, sin reapertura automática de captura.

Ajustes → Historial y búsqueda de capturas se activa por separado; abrir no guarda/reconoce. Solo capturas explícitas de región en Herramientas, OCR local en worker sin portapapeles/nube. Busca texto sin distinguir mayúsculas; error OCR conserva imagen con motivo en tooltip. Fecha local exacta YYYY-MM-DD, vacío muestra todo. Copiar, fijar, referencias, favoritos y borrar. capture-history.sqlite3 opcional junto ajustes: 10–200 capturas / PNG 8–128 MiB, cada una 16 MP/ocho MiB, base hasta 132 MiB más diarios. Borrar elimina texto; limpiar incluye favoritos; desactivar persistencia elimina base. Solo última captura pendiente, salta intermedias; cerrar descarta pendientes/resultados sin esperar OCR activo.

Widgets → Tareas y calendario ofrece casillas, vencimiento local opcional e importación UTF-8 .ics local de VEVENT/VTODO individuales. Hoy muestra incompletas sin fecha/vencidas/del día y eventos solapados; finales de todo el día/medianoche exclusivos. IANA TZID conocida con Qt, UTC se muestra local, floating local y fechas no cambian. DST: primera repetición/offset antes del salto; días DURATION nominales. UID+RECURRENCE-ID actualiza, SEQUENCE inferior se ignora, conserva casillas, CANCELLED elimina. Plegado/escapes TEXT; nunca abre enlaces/alarmas/adjuntos. RRULE/RDATE/EXDATE/zonas desconocidas se rechazan atómicamente, exportar ocurrencias individuales. tasks.json junto ajustes: 500 elementos/cuatro MiB, título 1000/descripción 2000 caracteres; escritura atómica conserva anterior si falla. Entrada cuatro MiB/línea 8192, sin red/sync/alarmas. Worker perezoso serializa archivos; cerrar para timers/resultados tardíos. Hoy participa en cierre/ocultación global, apertura explícita sin restauración automática; datos persisten.

Registros de cancelación cuentan en 500 e impiden que imports antiguos resuciten eventos. Limpiar todo pide confirmación y borra tareas, eventos y cancelaciones. Hoy usa pintado Qt software normal para evitar que el compositor cubra controles.

Ajustes → Biblioteca de recursos: imágenes/GIF, carpetas mascotas sprite, texturas .puppet, escenas JSON/.fescene con miniaturas estáticas, etiquetas, búsqueda sin mayúsculas y favoritos. No copia/borra/ejecuta; olvidar quita catálogo. asset-library.json junto ajustes: 200 entradas/un MiB, 32 etiquetas de 40 caracteres; imagen 64 MiB/16 MP, archivo 256 MiB, escena 256 capas. Escena estática con sustitutos de medios, Puppet primera textura. Referencias: escena actual, presets locales activos, JSON registrados (200/16 MiB), rutas ausentes conservadas. Relocalizar valida tipo y confirma referencias, edición anulable actual y reparación JSON/presets escribibles del espacio local y catálogo. Texto, historial inmutable, paquetes, escenas externas/Workshop solo lectura; copias importadas locales posibles. Cambios paralelos abortan. 50 archivos/16 MiB protegidos por diario atómico .asset-relink.json, recuperación antes del siguiente job; conflicto conserva diario. Candado OS .asset-library.lock protege otras instancias. Worker perezoso decodifica/lee/escribe, cerrar cancela escrituras pendientes y restaura edición actual sin cambios adicionales, ignora resultados tardíos. Reiniciar reproducción tras cambiar ruta.

Centro de control → Seguir ventana elige overlay registrado de nivel superior y objetivo Windows visible. Desplazamiento inicial proporcional sigue movimiento/tamaño; overlay lógico y posición física sin activar/redimensionar, limitada área de monitor, revisión 250 ms. Minimizar oculta, restaurar respeta ocultación manual/global; cerrar/ocultar/perder identidad desvincula. Propiedad única reversible + PID/thread evita HWND reutilizado; UIPI/objetivo elevado puede denegar. Desvincular antes de arrastrar nuevo offset. 64 enlaces temporales sin restaurar sesiones; cerrar/todos/salir quita cookies/para timer. Solo adaptador Windows verificado, otros muestran motivo. Ventanas propias en una pantalla 125% verificadas; DPI mixtos entre monitores requiere otra pantalla.

Centro de control → Perfiles de monitor guarda/restaura combinaciones (20 perfiles/200 ventanas/512 KiB local monitor-profiles.json). Posición proporcional adapta resolución/principal/DPI, tamaño lógico conservado; combinación nueva devuelve ventanas al principal. Automático opt-in separado, eventos Qt/nuevos overlays agrupados 500 ms, sin cambiar ajustes OS. Hardware ambiguo da error; mismo tipo/nombre no se guarda pero se recupera. Pantalla completa/escenas/seguidores excluidos; no crea overlays ni adivina handles. Solo coordenadas lógicas Qt. Verificado nativo en un Windows125%; conectar/desconectar, principal y DPI mixtos requiere más hardware.

Composición estática software reutiliza un frame ≤16 MP; contenido/DPR, transformación, opacidad, orden, clip, tamaño/DPI invalidan. Sin cambios no repinta, vídeo/animación sigue; GPU readback igual. Salir/Cerrar todos comparten registro: cerrar una vez antes de vaciar, restablecer fondos/cleanup antes de assets. Timer sin bloqueo mantiene Qt hasta acabar trabajos locales cancelados. Manifest API v1; examples/plugins/clock muestra QWidget overlay_widgets, release_overlay_resources/shutdown opcionales y get_state/set_state. Presets de plugins cargados bajo plugin:<nombre página>, rollback transaccional, sin cargar código. Copiar a plugins/, habilitar y aprobar digest, sin sandbox OS. Benchmark py -m benchmarks.scene_composition --output build/scene-benchmark.json, --baseline-file fiable opcional compara píxeles; datos/procedimiento docs/benchmarks/README.md.
