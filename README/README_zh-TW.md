# FrontEngine

<p align="center">
  <a href="../README.md">English</a> ·
  <strong>繁體中文</strong> ·
  <a href="README_zh-CN.md">简体中文</a> ·
  <a href="README_ja.md">日本語</a> ·
  <a href="README_ko.md">한국어</a> ·
  <a href="README_es.md">Español</a> ·
  <a href="README_fr.md">Français</a> ·
  <a href="README_de.md">Deutsch</a> ·
  <a href="README_pt-BR.md">Português (BR)</a> ·
  <a href="README_ru.md">Русский</a>
</p>

[![CI](https://github.com/JeffreyChen-SteamProjects/FrontEngine/actions/workflows/ci.yml/badge.svg)](https://github.com/JeffreyChen-SteamProjects/FrontEngine/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/frontengine)](https://pypi.org/project/frontengine/)
[![Python](https://img.shields.io/pypi/pyversions/frontengine)](https://pypi.org/project/frontengine/)

**把任何東西放在螢幕最上層——或是放到最底下。**

FrontEngine 是一款桌面覆蓋層應用程式。影片、圖片、GIF、網頁、文字、
粒子、音效與一隻會動的寵物，都能疊在其他所有視窗之上（可穿透點擊，
所以底下的東西照樣能用），或是放到它們後面當成動態桌布。除此之外還有
一整套針對螢幕本身的工具：護眼濾鏡、簡報標註、量測與擷取、專注遮罩與
桌面小工具。

[在 Steam 上支持這個專案](https://store.steampowered.com/app/2793470/FrontEngine/)
 · [說明文件](https://frontengine.readthedocs.io/en/latest/)
 · [觀看示範影片](https://youtu.be/fewogcb3b8Y)

![FrontEngine UI](../image/FrontEngine.png)

---

## 安裝

需要 Python **3.10+**。主要支援平台是 Windows 10/11；macOS 與 Linux 也能
執行這款應用程式，各平台的差異列在 [平台支援](#平台支援) 一節。

```bash
pip install frontengine

frontengine                    # or: python -m frontengine
frontengine --preset "Work"    # apply a saved preset on launch
```

預先編譯好的 Windows 執行檔在
[Releases 頁面](https://github.com/JeffreyChen-SteamProjects/FrontEngine/releases)，
Steam 版則是同一套應用程式，另外附帶 Workshop 支援。

> **怎麼離開。** 覆蓋層可以蓋滿整個螢幕，包括 FrontEngine 自己的視窗，
> 所以有兩條不需要用滑鼠的逃生通道：`Ctrl+Shift+F12` 會關閉每一個覆蓋層，
> 而 **F12 會直接結束整個應用程式**，在任何地方都能用（Windows；macOS 需輔助使用權限——
> 見 *Help → How to force close*）。

---

## 它會在螢幕上放什麼

側邊欄依用途把各頁面分組。本節依循這個分組。

### 螢幕上（On screen）

媒體覆蓋層。每一個都能選定自己的螢幕（或是橫跨所有螢幕）、記住你把它
拖到哪裡，並各自擁有自己的不透明度。

- **影片（Video）**——附音量、播放速率與循環。
- **圖片（Image）**——單一張圖片、把一個資料夾當成投影片播放，或是一塊
  **參考板**：多張圖片放在同一個畫布上，各自可拖曳，整塊板子可縮放、可平移。
- **網頁（Web）**——一個網址或一個本機 HTML 檔，可選擇是否可互動。
  **儀表板模式**會輪播一份網址清單，讓一面牆上的顯示器能靠快捷鍵或計時器
  循環切換頁面。
- **GIF / WebP**——可調速度的動畫。
- **文字（Text）**——字型、顏色、外框、對齊與跑馬燈，可顯示固定字串，
  或一個**即時來源**：時鐘、日期、倒數、碼表、系統負載或天氣。即時來源
  接受 `{field}` 樣板，頁面上會列出每一種來源提供的欄位。
- **音效（Sound）**——音樂播放與低延遲的 WAV 音效。
- **場景（Scene）**——把上面幾樣組成一個構圖，用一份可儲存、可分享的
  JSON 文件來描述。
- **粒子（Particle）**——一種 OpenGL 粒子效果。

<details>
<summary>螢幕截圖（GIF 可能需要一點時間載入）</summary>

| GIF | WebP |
| --- | --- |
| ![GIF](../gifs/play_gif.gif) | ![WEBP](../gifs/webp.gif) |

| Video | Website |
| --- | --- |
| ![Video](../gifs/video.gif) | ![Website](../gifs/website.gif) |

</details>

### 桌面（Desktop）

**桌面寵物（Desktop pet）**——一隻住在你桌面上、會動的精靈。

- **精靈圖（Sprites）**——單一個 GIF/WebP/PNG，或一個 *pet pack* 資料夾，
  其檔名對應到各種狀態：`walk`、`idle`、`sleep`、`climb`、`fall`、`drag`
  （缺少某個狀態時會退回用 `walk`）。可另外用一個 `pet.json` 設定大小、
  速度，以及它能不能爬牆、說話或坐在視窗上。
- **行為（Behaviour）**——在地板上帶重力地走動（把它丟出去會彈跳）、
  自由漫步，或追著游標跑。地板型寵物會爬螢幕邊緣，站在其他視窗的上緣。
- **生命（Life）**——心情、飽足度與一個好感度，都會在多次執行之間保留。
  它會隨著升級而長大、用對話框說話、在你離開時打盹，並在電量偏低時提醒你。
- **互動（Interaction）**——拖曳它、右鍵複製／餵食／設定提醒，還能
  **把檔案拖放到它身上**：圖片或 pet pack 會變成它的新造型，其他東西則會
  被吃掉。吃什麼很有講究——壓縮檔是一頓大餐，音樂讓它開心的程度大於填飽的
  程度，文件是一頓普通餐點，二進位檔則太難嚼了。
- **鬼抓人（Tag）**——螢幕上有兩隻以上的寵物時，勾選 *Play tag with each
  other*，其中一隻會變成「鬼」：它會朝最近的鄰居走去，其他寵物則往反方向跑，
  抓到某一隻就把「鬼」傳出去。
- **對聲音有反應（Reacts to sound）**——寵物會隨你喇叭的輸出而跳動，或是
  隨你的**麥克風**跳動，讓它在你說話時跟著動。兩者都只讀取輸出的*音量計*
  ——一個數字，而不是音訊本身。峰值會經過一個 RMS 視窗與一條快速上升／
  緩慢衰減的包絡線平滑處理，讓跳動像呼吸而不是閃爍。有多台螢幕時，每隻寵物
  會跟隨對應自己螢幕的那個音訊端點。
- **專注計時器（Focus timer）**——同一頁上的番茄鐘，由寵物來播報：它會
  在專注結束時、以及休息結束時告訴你。
- **聊天（Chat）**——設定了 `ANTHROPIC_API_KEY` 時，寵物可以透過 Claude
  回答你。除非你啟用，否則預設關閉；見 [有什麼會離開這台機器](#有什麼會離開這台機器)。

**桌布（Wallpaper）**——把一整個資料夾的圖片與動畫播放在每一個視窗*底下*。
每台螢幕各自指向自己的資料夾、各自有自己的計時器，可打亂順序或遞迴讀取，
並可隨喇叭音量跳動。在安靜時段可由第二個資料夾接手。

**小工具（Widgets）**——四樣坐在桌面上的東西：

- **音訊頻譜（Audio spectrum）**——長條或圓環、對數間隔的頻段，經一條
  快速上升／緩慢衰減的追蹤器平滑處理，並有會慢慢往下飄的峰值標記。
- **正在播放（Now playing）**——在安裝了選用的 `winsdk` 綁定時，顯示
  Windows 媒體控制中目前的曲目；否則顯示實際正在發出聲音的那個應用程式名稱。
- **系統監視器（System monitor）**——把 CPU、記憶體、磁碟、電池與網路
  吞吐量顯示成小小的走勢線；勾選你想要的那幾條線。平均值會藏住卡頓；
  一條線不會。隱藏的線仍持續記錄，所以重新打開時會顯示這段期間發生了什麼。
- **便利貼（Sticky notes）**——浮在每個視窗之上、可編輯的卡片，會在多次
  工作階段之間保留文字、顏色與位置。

### 工作（Work）

**專注（Focus）**——當螢幕在跟你的工作搶注意力時的兩種覆蓋層。
*Dim background windows* 會把你正在使用的視窗以外的一切都調暗，強度可調整。
*Cover a distraction* 會遮住螢幕上的一條區域：工作列、通知角落、某個邊緣，
或整個螢幕。兩者都會讓點擊穿透，所以它們遮住的東西照樣能用——只是不再
把你的目光拉過去。

**護螢幕（Screen care）**——給長時間盯著螢幕的場合：

- **色彩濾鏡（Colour filter）**——七種色調，從暖色經琥珀、玫瑰色到灰色，
  強度可調整。
- **閱讀尺（Reading ruler）**——把頁面調暗，只留一條跟著游標移動的亮帶。
- **休息提醒（Break reminder）**——20-20-20 法則，時間到時會出現一個
  休息覆蓋層。
- **色覺模擬（Colour-vision simulation）**——紅色盲、綠色盲、藍色盲與
  全色盲，嚴重程度可調整，採用 Machado 等人（2009）的模型。與其他覆蓋層
  不同，這一個是不透明的，因為要呈現別人眼中所見，就得重畫整個螢幕，
  而不是替它上色。

**簡報（Presenting）**——給示範、教學與錄影：

- **標註（Annotation）**——用筆、螢光筆或橡皮擦在螢幕上畫，附還原與清除。
- **游標效果（Cursor effects）**——指標周圍一圈光環、點擊時的漣漪，以及
  一道把其他部分調暗的聚光燈。
- **按鍵顯示（Keystroke display）**——顯示你剛按下什麼，以及你按了哪個
  滑鼠鍵，好讓觀看的人跟得上；它會在幾秒後淡出。可以挑面板要放在哪裡、
  文字要多大，也可以單獨關掉滑鼠點擊。
- **放大鏡（Magnifier）**——游標周圍區域的放大檢視。
- **白板（Whiteboard）**——一塊無限大的畫布：拖曳可平移、捲動可縮放、
  可儲存你畫的東西。筆畫存在畫布座標裡，所以平移與縮放時它們都會留在
  該在的位置。
- **凍結（Freeze）**——把某台螢幕目前的畫面釘住，讓你可以在一張靜止影像
  後面繼續工作。`Ctrl+Shift+F7` 會解除它，這很重要，因為凍結的影像會蓋住
  本來要按的那個按鈕。

**工具（Tools）**——量測、擷取與視窗處理：

- **色彩選取器／像素尺／量角器（Colour picker / pixel ruler / protractor）**
  ——點一下就取樣或量測；結果會直接進到剪貼簿，格式為 `#rrggbb`、
  `rgb(...)`、`hsl(...)` 或一個 CSS 自訂屬性。
- **區域擷取（Region capture）**——拖出一塊區域；它會進到剪貼簿、可存成
  檔案，或**釘**在最上層成為一份可縮放的浮動副本。
- **錄製區域（Record area）** — 錄製：框選範圍後，先選擇輸出 GIF 才開始擷取；取消不會啟動錄製。影格由背景執行緒逐張寫入，佇列上限為三張與 64 MiB，單張超限會拒絕。佇列已滿時略過擷取，並保留實際經過的播放時間。仍保留幀率、時長、影格數上限與攝影機子母畫面。停止後非同步完成寫檔，只有成功時才原子替換目標；取消與寫入失敗會清除暫存檔，保留既有目標檔。
- **相機（Camera）**——把你的網路攝影機放進一個圓形、圓角方框或矩形，
  只在本機顯示，絕不錄下。任何視訊輸入都能用，包括擷取卡，而且裝置清單
  不用重新啟動就會刷新，因為擷取卡通常是在應用程式已經在跑的時候才插上。
- **虛擬攝影機（Virtual camera）**——把一塊區域連同所有覆蓋層一起，送成一個
  網路攝影機，讓 Zoom、Teams 或 Discord 能把它選為視訊來源。需要選用的
  `pyvirtualcam` 套件與一個虛擬攝影機驅動程式（OBS 會裝一個）；少了任一項，
  按鈕會明講，而不是默默失敗。
- **讀取文字（Read text）** — 畫面文字：Tools → Read text 優先使用本機 OCR：Windows 的 Windows.Media.Ocr、macOS 的 Vision，或已安裝且具有語言資料的 Tesseract 執行檔。本機擷取文字不需雲端同意或 ANTHROPIC_API_KEY；成功但沒有文字時不會上傳截圖。翻譯與提問只有在另行同意傳送文字且提供金鑰時，才會將辨識文字送至 Anthropic。本機失敗後的截圖回退需要獨立的畫面傳送同意與金鑰。結果會顯示後端及錯誤，也能撤回同意。
- **釘住視窗（Pin a window）**——在你對照它工作時，把另一個程式的視窗保持
  在最上層，或讓它淡出。只動到堆疊順序與不透明度，絕不碰視窗內容。
- **視窗複本（Window replica）**——另一個視窗的一份小小的、永遠置頂的即時
  副本，讓你能在某個算圖或某段對話被埋住時仍看著它。
- **視窗版面（Window layouts）**——儲存每個視窗的位置，稍後再把它們放回去。
  視窗以標題比對；不在螢幕上的視窗會被略過，而不是用猜的。

---

## 一次控制全部

**控制中心（Control center）**頁面能觸及每一頁上的每一個覆蓋層，無論它是
從哪個分頁開啟的：隱藏、顯示、關閉、靜音、鎖定、重設位置、逐級調整不透明度，
並套用一個 **品質層級（quality tier）**（高／平衡／省電），為每個覆蓋層的
刷新率設上限並降低其算圖解析度。它還帶著一個給 OBS 用的色鍵背景、一個
*Hide from capture* 開關、記錄面板，以及 **Pin to this desktop**——你切換
虛擬桌面時覆蓋層會讓開，回來時再回來。取消釘選會把它收起來的東西都帶回來。

預設的全域快捷鍵，全部都可在 **Settings → Hotkeys** 重新綁定：

| 快捷鍵 | 動作 |
| --- | --- |
| `Ctrl+Shift+F12` | 關閉每一個覆蓋層 |
| `Ctrl+Shift+F11` / `F10` | 隱藏／顯示每一個覆蓋層 |
| `Ctrl+Shift+F9` | 全部靜音 |
| `Ctrl+Shift+↑` / `↓` | 不透明度提高／降低 |
| `Ctrl+Shift+L` | 鎖定或解鎖（穿透點擊 vs. 可拖曳） |
| `Ctrl+Shift+→` | 下一個儀表板頁面 |
| `Ctrl+Shift+F8` | 在螢幕上顯示快捷鍵一覽表 |
| `Ctrl+Shift+F7` | 凍結／解除凍結螢幕 |
| `Ctrl+Shift+F6` / `F5` / `F4` | 媒體播放/暫停、下一首與上一首 |
| `Ctrl+Shift+F3` | 把前景視窗移到下一台螢幕 |
| `F12` | 立即結束（Windows / macOS*） |

媒體傳輸送的是系統媒體鍵，所以它能觸及任何會監聽這些鍵的播放器。移動視窗
時會保持它的比例，而不是把它硬切過去，後者正是 Windows 自己的
`Win+Shift+Arrow` 的做法。

遠端遙控所驅動的，就是這些相同的動作——不多不少：

- **你的手機**（Settings → Remote control）——FrontEngine 會在你的區域網路
  上提供一個小頁面；在手機上打開那個連結，按鈕就會驅動那些動作。
- **一個 MIDI 控制器** — 按 Learn，轉動旋鈕或按 pad 即可綁定。Windows 使用內建 winmm；macOS 透過 macos extra 使用 CoreMIDI。旋鈕到頂端只觸發一次，放開 pad 不算再次按下。

---

## 預設集與自動化

**預設集（Presets）**會一次擷取每一頁的設定。你可以從 **Presets** 選單
儲存、載入、刪除、匯出與匯入它們、在啟動時套用其中一個，或自動還原上一次的
工作階段。一個預設集可以匯出成一個**套件（package）**——一個帶著它所引用媒體
的 zip 檔——所以它在沒有那些檔案的機器上也能打開。

接下來是一些會自己做決定的東西，全都在 **Settings** 選單裡。Smart pause
是唯一一個一開始就開著的；其餘的在你打開之前都是關的。

| | |
| --- | --- |
| **Rules** | *「當這些條件成立時，就做這件事。」* 結合一個星期幾、一個時間區間，以及哪個應用程式取得焦點，然後套用一個預設集、隱藏/顯示/關閉覆蓋層，或設定品質。空白條件代表「任何」，而一條規則會在它的條件開始成立時執行**一次**，而不是在成立期間反覆執行。這是唯一一處條件會組合起來的地方；下面各列各自只認得單一種類。 |
| **Smart pause** | 在全螢幕應用程式執行時、在機器使用電池時，或在某個指定的應用程式取得焦點時，讓覆蓋層退下。*（預設開啟，用於全螢幕那條規則。）* |
| **App profiles** | 在你切換到某個指定應用程式時套用一個預設集。 |
| **Preset schedule** | 在選定的星期幾、指定的時間套用一個預設集。 |
| **Theme schedule** | 依時鐘在日間主題與夜間主題之間切換。 |
| **Signage mode** | 收起主視窗，依計時器輪播一份預設集清單，適合一台長時間開著當顯示器用的機器。 |
| **Screensaver** | 閒置超過某個門檻後，帶出你選的影片／圖片／GIF／粒子／網頁，並在你回來時把它收掉。 |
| **Reminders** | 每 N 分鐘,或每天在指定時間一次,以會自己關閉的浮動通知顯示。 |
| **Keep awake** | 在覆蓋層開著時阻止螢幕進入睡眠。 |
| **Start with the system** | 在登入時啟動。 |
| **Screen time** | 哪些應用程式取得過焦點、各持續多久，附每日明細與七天摘要。你離開鍵盤時它會暫停,最多保留 60 天,而清除會把檔案本身刪掉。 |
| **Clipboard history** | 搜尋你複製過的內容,並釘住你會重複使用的字句。剪貼簿經常存著密碼,所以除非你另外勾選「keep between sessions」,否則這是**只存在記憶體裡**的。 |

---

## 語言

七種:English、繁體中文、简体中文、Deutsch、Русский、Français、Italiano。

從 **Language** 選單挑一種,介面就會**立刻**改變——不用重新啟動。你原本
開著的東西都會保持開著:覆蓋層繼續執行,每一頁的設定也都維持原樣。在 Steam
安裝版上,第一次啟動會跟隨 Steam 用戶端自己的語言。

---

## 隱私與平台注意事項

### 有什麼會離開這台機器

FrontEngine 裡的一切都是在本機進行的,除非它在這份清單上。有四個例外,
全部都是需要主動選擇加入(opt-in)的:

| 功能 | 送到哪裡 | 防護 |
| --- | --- | --- |
| **Read text**(Tools) | Anthropic API | 畫面文字：Tools → Read text 優先使用本機 OCR：Windows 的 Windows.Media.Ocr、macOS 的 Vision，或已安裝且具有語言資料的 Tesseract 執行檔。本機擷取文字不需雲端同意或 ANTHROPIC_API_KEY；成功但沒有文字時不會上傳截圖。翻譯與提問只有在另行同意傳送文字且提供金鑰時，才會將辨識文字送至 Anthropic。本機失敗後的截圖回退需要獨立的畫面傳送同意與金鑰。結果會顯示後端及錯誤，也能撤回同意。 |
| **Pet chat** | 你的訊息會送到 Anthropic 的 API | 同一把金鑰、同一條規則;預設關閉。 |
| **Weather**(文字來源) | 座標會送到 Open-Meteo | 不需要金鑰、不需要帳號、沒有任何可識別身分的資料;只有你當成地點輸入的那些內容。 |
| **Phone remote** | HTTPS | 手機操控：Settings → Remote control 只提供 HTTPS，權杖每次啟動都會更換，可執行動作採固定清單。手機不會自動信任本機自簽憑證。請先匯出公開憑證，比對顯示的 SHA-256 指紋，再依手機或瀏覽器設定匯入或信任。私鑰留在使用者資料目錄。IP 變更、到期或重新產生憑證時，可能需信任新憑證。TLS 啟動失敗不會退回 HTTP。 |

音訊功能只讀取一個輸出**音量計**——單一個數字——只有頻譜例外,它需要真正的
取樣來計算頻率,因此會擷取系統輸出串流。那些取樣是在記憶體裡分析的,絕不
寫到磁碟或送到任何地方,而且你一停止頻譜,擷取就立刻停止。

外掛：啟用載入不代表授權外掛。plugin.json 或單檔 sidecar 宣告版本、身分、入口與能力；Python import 前檢查同意，授權綁定內容摘要。程式或宣告改變就需重新同意；舊外掛需明確完全信任。Settings → Revoke plugin grants 可撤銷保存的授權；已在執行的程式需重新啟動才能卸載。Python 外掛仍具有完整應用程式權限，宣告與同意不是作業系統沙箱。

### 螢幕分享隱私

你的覆蓋層是給你自己看的,不是給你正在分享的對象看的。從
**Settings → Screen-sharing privacy**,FrontEngine 可以在會議應用程式開著時
把它們排除在擷取之外:

- **它們會留在你自己的螢幕上。** 只有被擷取的那份副本是空白的——這用的是
  Windows 的 `WDA_EXCLUDEFROMCAPTURE`,一個作業系統層級的旗標,會議與錄影
  應用程式都會遵守它。
- **遮罩是例外。** 一個干擾遮罩的存在就是為了蓋住某樣東西,所以它會刻意
  在擷取中保持可見。
- **觸發依據是你的清單。** Windows 沒有可靠的「我是不是正在被擷取」API,
  所以它會盯著你指名的視窗標題——這也能抓到在瀏覽器分頁裡開的會議,那種
  情況下執行檔就只是瀏覽器而已。

控制中心裡也有一個手動的 *Hide from capture* 按鈕。

> 這是隱私,不是資安:它擊敗的是一般的擷取路徑,而且它從不對坐在桌前的
> 那個人隱藏任何東西。

### 平台支援

這裡沒列出來的一切,在三個平台上都能運作。

| 功能 | Windows | macOS | Linux |
| --- | :---: | :---: | :---: |
| 一般覆蓋層與介面 | ✅ | ✅ | ✅ |
| 系統音訊、頻譜與麥克風 | ✅ | backend* | — |
| 正在播放的曲目資訊 | ✅ | — | — |
| 視窗幾何、版面與跨螢幕移動 | ✅ | backend* | — |
| 即時視窗複本 | ✅ | backend* | — |
| 其他視窗強制置頂／不透明度 | ✅ | — | — |
| 擷取時排除覆蓋層 | ✅ | — | — |
| MIDI 控制 | ✅ | backend* | — |
| 媒體操作鍵 | ✅ | backend* | — |
| 虛擬桌面／Space 指定 | ✅ | — | — |
| F12 緊急退出 | ✅ | backend* | — |
| 寵物站在其他視窗上 | ✅ | backend* | wmctrl |

* macOS 標示 backend 的項目需 macos extra、macOS 13+ 與對應權限。這表示已實作公開 framework 路徑，並非已在本 Windows 環境完成 macOS 實機驗證；見下方執行環境說明。

在某個功能無法運作的地方,按鈕會明講,而不是默默失敗。

---

## 執行環境、隱私與互通

錄製：框選範圍後，先選擇輸出 GIF 才開始擷取；取消不會啟動錄製。影格由背景執行緒逐張寫入，佇列上限為三張與 64 MiB，單張超限會拒絕。佇列已滿時略過擷取，並保留實際經過的播放時間。仍保留幀率、時長、影格數上限與攝影機子母畫面。停止後非同步完成寫檔，只有成功時才原子替換目標；取消與寫入失敗會清除暫存檔，保留既有目標檔。

手機操控：Settings → Remote control 只提供 HTTPS，權杖每次啟動都會更換，可執行動作採固定清單。手機不會自動信任本機自簽憑證。請先匯出公開憑證，比對顯示的 SHA-256 指紋，再依手機或瀏覽器設定匯入或信任。私鑰留在使用者資料目錄。IP 變更、到期或重新產生憑證時，可能需信任新憑證。TLS 啟動失敗不會退回 HTTP。

畫面文字：Tools → Read text 優先使用本機 OCR：Windows 的 Windows.Media.Ocr、macOS 的 Vision，或已安裝且具有語言資料的 Tesseract 執行檔。本機擷取文字不需雲端同意或 ANTHROPIC_API_KEY；成功但沒有文字時不會上傳截圖。翻譯與提問只有在另行同意傳送文字且提供金鑰時，才會將辨識文字送至 Anthropic。本機失敗後的截圖回退需要獨立的畫面傳送同意與金鑰。結果會顯示後端及錯誤，也能撤回同意。

Puppet 寵物：安裝選用的 puppet extra 與可用的 Imervue runtime，再於寵物頁選擇或拖入原始 Imervue .puppet v1 檔案。既有圖片與 sprite 寵物包仍可使用。Puppet 寵物使用 Imervue 畫布、動作與表情，可複製或關閉，並支援 FrontEngine 覆蓋層控制與預設集。可另選 .petscript.json 使用 Imervue 原有腳本引擎；FrontEngine pet.json 寵物包不是 puppet 檔。未知版本、不安全的封存路徑與無效資源會在載入 runtime 前拒絕。

場景：場景頁支援舊 entry mapping JSON、有版本的 frontengine.scene envelope，以及可攜式 .fescene 套件。PUPPET 項目可設定位置、大小、不透明度、有限數值參數，以及選用動作、表情與腳本。JSON 路徑相對於場景檔解析。.fescene 包含引用媒體、原始 .puppet 與選用 .petscript.json，可移到其他電腦。匯入會檢查路徑、符號連結、版本與解壓上限。FrontEngine 場景維持場景套件；.puppet 維持單一 Imervue 角色。

macOS：選用 macos extra 以 macOS 13+ 與公開 PyObjC framework 為基準。後端提供 ScreenCaptureKit 螢幕／視窗擷取與系統音訊、麥克風擷取、Quartz 視窗幾何、Accessibility 視窗版面與移動、CoreMIDI、媒體鍵及 F12 退出。螢幕錄製、輔助使用與麥克風權限分別檢查；請到系統設定 → 隱私權與安全性，依提示重新啟動。其他程式視窗的透明度／強制置頂、Space 指定，以及讓其他程式擷取時排除覆蓋層仍不可用。本 Windows 開發環境尚未驗證 macOS 原生授權、硬體與效能。 Settings → macOS 權限與能力會逐項列出可用、不可用或不支援，並顯示權限或安裝原因。

外掛：啟用載入不代表授權外掛。plugin.json 或單檔 sidecar 宣告版本、身分、入口與能力；Python import 前檢查同意，授權綁定內容摘要。程式或宣告改變就需重新同意；舊外掛需明確完全信任。Settings → Revoke plugin grants 可撤銷保存的授權；已在執行的程式需重新啟動才能卸載。Python 外掛仍具有完整應用程式權限，宣告與同意不是作業系統沙箱。

算圖：Settings → Overlay rendering 可選 Auto、GPU 或 Software，並查看實際後端。GPU 合成器以 OpenGL texture、shader 與 framebuffer 處理圖層順序、變換、不透明度與裁切；初始化失敗時回退軟體並顯示原因。既有 QPainter 內容仍可能先由 CPU 轉成點陣圖再上傳；web／video／原生 widget 可能使用獨立視窗。擷取與錄製可能將 GPU 畫面讀回 CPU，這不代表零拷貝擷取或已測得效能提升。

Windows OCR 的 WinRT 投影套件包含於 FrontEngine 的一般 Windows 安裝；請安裝需要的 Windows 辨識語言。Tesseract 的執行檔與訓練語言資料需另行安裝。選用 puppet extra 會安裝 Imervue>=1.0.90；macos extra 安裝 macOS 13+ 的公開 PyObjC framework。請使用下列指令。docs/formats/ 提供 puppet、pet.json、petscript 與場景範例。

```bash
pip install "frontengine[puppet]"
pip install "frontengine[macos]"
```

[.puppet / pet.json / .petscript.json / .fescene](../docs/formats/interoperability.md)

---

## 擴充

- **Steam Workshop**——訂閱的項目會從 Steam 自己的
  `steamapps/workshop/content` 資料夾撿取:預設集會被匯入,pet pack 會連同
  它們的路徑一起列出,從 **Presets → Import Workshop content**。要發佈到
  Workshop 需要 Steamworks SDK,並未內建。
- **外掛(Plugins)**——一個 `plugins/` 資料夾可以加入它自己的分頁,可透過
  一個 `FRONTENGINE_TABS = {"name": WidgetClass}` 對應,或一個
  `register(registry)` 掛勾。請先讀上面那則信任提醒。

---

## 開發

```bash
pip install -r dev_requirements.txt
pip install -e .

python -m pytest tests/ -q          # the whole suite, headless (Qt offscreen)
```

靜態檢查使用 pyflakes(在 `dev_requirements.txt` 裡),一棵乾淨的樹會什麼都
不印出來:

```bash
python -m pyflakes frontengine/ exe/ tests/
```

測試套件完全在螢幕外(offscreen)執行,不需要顯示器、音效卡或相機;任何會
接觸到外部世界的東西都採用一個可注入的來源,所以能用一個假的來測試。

- **架構(Architecture)**——[`architecture_explore.md`](../architecture_explore.md)
  對應到每一個模組、分層、覆蓋層契約與擴充點。在新增一個頁面或一個覆蓋層
  之前先讀它:有好幾樣東西(控制中心登錄、七份語言字典、七棵文件樹)必須
  一起更新,而測試會強制這一點。
- **貢獻(Contributing)**——見 [`CONTRIBUTING.md`](../CONTRIBUTING.md)。一個
  pull request 一個功能,所有 CI 檢查都要是綠的。
- **建置 Windows 執行檔**——`python exe/build_exe.py`
  (Nuitka;加上 `--onefile` 產生單一檔案)。
- **說明文件(Documentation)**——Sphinx 原始碼在 `docs/` 裡,以全部七種
  語言發佈到 [Read the Docs](https://frontengine.readthedocs.io/en/latest/)。

---

## 持續整合與發佈

工作流程是 `feature → dev → main`,而且只有最後一步會發佈:

```
feat/xyz  ──PR──►  dev  ──PR──►  main
                    │              │
              CI, no release   CI + release
```

| 工作流程 | 觸發 | 用途 |
| --- | --- | --- |
| `CI`(`ci.yml`) | 推送／PR 到 `main` 或 `dev`、手動派發,或由 `Nightly` 呼叫 | 編譯、跑單元測試,接著從*那次 checkout* 建置一個 wheel、安裝它並啟動應用程式——在 Python 3.10 / 3.11 / 3.12、Windows 上 |
| `Nightly`(`nightly.yml`) | 每日 cron、手動派發 | 呼叫 `CI`。排程刻意放在這裡:GitHub 會在含有 cron 的工作流程閒置約 60 天後停用它,否則那會連帶把 PR 檢查一起弄掉 |
| `Release`(`release.yml`) | 一個**來自 `dev`**的 pull request 被併入 `main`,或手動派發 | 提升版本號、帶著 `[skip ci]` 把它 commit 回去、把 `stable.toml` → `pyproject.toml` 對調、建置 sdist + wheel、以 `frontengine` 之名上傳到 PyPI、建立一個標記為 `v<version>` 的 GitHub release,並快轉 `dev` |

發佈**只在 `dev` 併入 `main` 時**發生。功能落在 `dev` 上而不鑄造版本號,
而一次發佈是一個刻意為之的 `dev → main` pull request。一個誤把目標指向
`main` 的功能 PR 仍會被併入,但不會發佈——失敗的方向是漏了一次發佈,
而不是多了一次不想要的發佈。

修訂號(patch)區段會自動提升;至於次版本或主版本發佈,執行
*Actions → Release → Run workflow* 並挑選區段。那條路徑也能在不需要新的
併入之下,重跑一次失敗的發佈。

版本號存在兩個檔案裡:`pyproject.toml` 是開發套件(`frontengine_dev`),
`stable.toml` 是已發佈的那一個(`frontengine`)。

需要一個 repository secret:`PYPI_API_TOKEN`,一個範圍限定在 `frontengine`
專案的 PyPI 權杖。工作流程用 `__token__` 當作 twine 使用者名稱,所以只需要
存權杖本身。

---

## 授權

見 [`LICENSE`](../LICENSE)。社群期待寫在
[`Contributor_Covenant_Code_of_Conduct.md`](../Contributor_Covenant_Code_of_Conduct.md)。

Workshop 內容宣告採版本化格式，使用前會驗證；未知的中繼資料 JSON 不會當成預設集。預設集封包會拒絕不安全的封存路徑、超出資源上限及媒體檔名碰撞。

預設集 → 管理創意工坊可開啟 Steam 管理介面；場景與寵物頁也提供入口。Windows x64 需已連線 Steam 客戶端、App 2793470 工作階段及 steam_api64.dll。可發布已儲存的 .fescene／場景 JSON、預設集 ZIP 或 sprite 寵物資料夾，並附小於 1 MB 的 PNG/JPEG 預覽。新項目預設私人，更新時核對擁有者。上傳顯示進度與條款狀態，保存項目 ID 供重試，隱藏管理視窗仍繼續；中斷後須在 Steam 確認結果。訂閱內容先驗證並複製到獨立版本資料夾，本機修改衝突可選下載版本或本機版本。載入會填入對應功能頁，播放從該頁啟動；預設集匯入須使用新名稱。既有離線資料夾匯入保留。Steam 封裝時於 exe/build_exe.py 加上 --steam-runtime DLL路徑，選定 DLL 放在執行檔旁（--onefile 亦同），不包含整套 SDK 或開發用 steam_appid.txt。

Windows 安裝現在包含 winrt-Windows.Media.Control，讓「正在播放」小工具透過 SMTC 顯示歌名與演出者；舊 winsdk 仍可備援。沒有媒體工作階段時回傳空結果，並保留既有音訊程式名稱備援。

執行檔建置會在編譯前檢查所有必要依賴與版本；請先在建置環境安裝 requirements.txt。

場景 → 視覺編輯提供圖片／GIF／文字圖層清單與預覽、群組拖曳、角落縮放、位置／尺寸／倍率／旋轉／順序／透明度控制、畫布對齊、位置鎖定、顯示、複製及 100 步復原／重做（Ctrl+Z／Ctrl+Y）。可直接匯出可攜 .fescene；腳本頁也能編輯並套用 JSON。播放會還原明確尺寸、倍率、旋轉與顯示狀態。載入／套用外部 JSON 時開啟新的復原紀錄，保留既有欄位。

從選單列開啟「功能搜尋」，或在 FrontEngine 按 Ctrl+K／Ctrl+Shift+P。可搜尋目前介面語言、英文名稱或固定命令名稱；上下鍵選取，Enter 執行。包含頁面導覽、擷取、便利貼、護眼濾鏡、Workshop 與既有全域動作。預設集／畫質動作可輸入值。收藏及最近 20 個命令會在重開後保留；參數及搜尋文字不會保存。

文字 → 本機 TXT／JSON／CSV 可選取 UTF-8 檔案、欄位及 1–3600 秒更新間隔。JSON 欄位使用 /鍵/索引（例如 /build/tasks）；CSV 使用不重複欄名，選取欄以多行顯示。欄位留空顯示整份檔案。背景讀取每個來源最多一項進行中工作，輸入上限 1 MiB、輸出上限 65,536 字元。檔案／欄位缺失、格式、權限與大小限制均有明確狀態，修正後自動恢復。預設集保存檔案、欄位及間隔。可攜場景會複製選取的資料檔，分享封包會分享該份資料快照。

工具 → 色票管理可在勾選「收集色票」後，透過取色器連續點選收集顏色。可命名、分組、編輯精確色碼、搜尋、複製及移除，近期取樣可重用。本機保存最多 512 張色票及 50 個不同近期顏色，重開後保留。每組名稱不分大小寫且不可重複，重複時明確拒絕。CSS／JSON 匯出保留 RGB 色值；CSS 變數名稱碰撞會加數字尾碼。匯出採完整寫入後取代檔案。功能搜尋也可開啟色票管理。

預設集 → 預設集版本會跨工作階段保留每個預設集最多 50 個不同設定快照。儲存時記錄原配置與新配置，相同內容不重複保存。選取版本可比較與目前分頁設定的欄位差異；預覽會將該配置套用至分頁控制項，取消預覽、Escape 或關閉視窗會回復原設定。「回復版本」會套用並存檔，若套用或儲存失敗則還原分頁設定。快照只保留媒體路徑，不複製媒體；預覽不開啟覆蓋層。既有 JSON／ZIP 預設集保持相容。歷史位於 presets/.versions；刪除預設集後歷史仍保留，同名重建時可查看。

寵物 → 寵物身分與存檔會為每隻 sprite 或 Puppet 寵物保存獨立 UUID、名字、心情、飽足及好感度。重開後於生成前選取已保存身分即可接續狀態；「新寵物」建立新狀態。第一個身分只遷移一次原共用數值。複製會將目前數值複製到新身分，餵食不會改到其他寵物。可重新命名、整理、匯出或匯入單隻 JSON 存檔，匯入一定建立新身分。同一個身分同時只能啟用一次。存檔不含圖片、腳本或對話紀錄，可攜預設集不寫入本機身分 ID。使用者設定最多保存 256 個身分；sprite 數值變更稍後合併存檔，關閉時也會保存。Puppet 餵食只更新存檔數值，不改變 Imervue 動作及尺寸。

圖片 → 比較圖片可在同一個縮放／平移視窗檢視兩張參考圖，切換並排、透明疊圖、滑動分隔線與 RGB 絕對差。可不縮放而對齊左上角或中心，或保持比例將 B 放入 A。滾輪同步縮放；滑桿調整 B 透明度或分隔線位置。透明像素與留白以白底比較，差異黑色表示 RGB 相同；動態圖片只用第一影格。解碼、對齊及差異計算在背景執行，每次只處理一個請求並套用最新選擇；透明度／分隔線重繪沿用圖片快取。每檔限 64 MiB、單邊最多 8,192 像素，每圖及對齊畫布最多 16,777,216 像素。新選擇失敗會保留原比較內容，關閉會釋放圖片並忽略遲到結果。

設定 → 規則新增優先數字（-1000…1000）、冷卻時間（0…86400 整數秒）、條件預覽及本工作階段執行紀錄。觸發規則由小到大執行，相同數字依表格順序，較高優先數字最後執行。冷卻依單調時鐘計算，期間觸發會消耗並略過，期滿時若條件仍成立也不執行。預覽可檢查未存檔的列，不執行動作或消耗觸發。最近 200 筆紀錄保留規則條件、當時環境與派送／執行／失敗／冷卻結果，只存在記憶體。已命名但無效的列會阻止存檔。最多 200 條規則，同名規則也有獨立身分；編輯時保留表格未列出的既有條件。動作回報失敗時會記錄失敗，不阻斷後續規則。

規則可載入、播放或停止場景，並顯示、隱藏、移動指定圖層或設定透明度。選取規則列後按「選擇場景／圖層目標」，可瀏覽 JSON、.fescene 或 .puppet，選擇主螢幕、所有螢幕或編號螢幕，以及目前編輯器的圖層。播放路徑留空時使用目前場景。檔案在背景讀取；新場景建立失敗會保留原播放內容。最新場景要求會取代先前未完成的要求；其後的圖層動作等待載入，載入失敗時一併失敗。鎖定或不存在的圖層會被拒絕。圖層修改可復原並同步播放；透明度為 0–100，位置限制為 ±100000。停止會取消待處理要求並關閉播放，編輯素材保留至替換或程式關閉。執行紀錄反映背景動作的實際結果。命令面板也有這些動作：可填路徑或 {"path":"scene.fescene","screen":"primary"}，顯示／隱藏填圖層鍵名，透明度填 {"layer":"title","opacity":50}，位置填 {"layer":"title","x":20,"y":30}。

場景 → 腳本 → 情境範本（亦可由命令面板開啟）提供工作桌面、教學與專注配置，附目前語言的可修改文字。先預覽並選擇主螢幕或編號螢幕，再按「套用並播放」；配置會依該螢幕的可用邏輯尺寸等比例調整。範本已包含所需素材；素材缺失時會列出圖層／欄位／路徑並禁止套用。套用透過既有場景建立流程替換編輯內容與播放，準備失敗會保留原場景。之後可修改文字、加入素材，再由場景匯出另存 JSON 或可攜 .fescene。關閉範本庫只會取消自身待處理的套用。專注範本提供可修改的提醒文字，排程與計時器仍由各自工具設定。

場景 → 視覺編輯可在圖片／GIF／文字之外加入影片、網頁、Puppet 與音訊。須手動啟用即時預覽，最多八個來源，預設靜音；試聽選取媒體才開啟聲音，隱藏時暫停，停用或關閉時釋放資源。影格每邊最多 1280 像素，無法預覽會顯示原因。具名場景播放將影片影格、網頁自己的渲染畫面及 Imervue 離屏 Puppet 影格依順序與所有視覺圖層合成；音訊播放不顯示圖層。播放時雙擊網頁／Puppet，或在編輯器選擇與選取媒體互動，可開啟同一個原生輸入視窗。Puppet 預覽需要原生 OpenGL 與選用執行環境，不執行寵物腳本，場景寵物採用暫存狀態。獨立網頁／影片／Puppet 視窗仍可使用。JSON／.fescene 匯出保留全部支援類型與素材引用。
