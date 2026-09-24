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
> 而 **F12 會直接結束整個應用程式**，在任何地方都能用（僅限 Windows——
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
- **錄製區域（Record area）**——把一塊區域錄成動畫 GIF，並把相機合成到角落，
  做出反應影片的效果。長度與影格數兩者都有上限，因為每一格都保存在記憶體裡。
- **相機（Camera）**——把你的網路攝影機放進一個圓形、圓角方框或矩形，
  只在本機顯示，絕不錄下。任何視訊輸入都能用，包括擷取卡，而且裝置清單
  不用重新啟動就會刷新，因為擷取卡通常是在應用程式已經在跑的時候才插上。
- **虛擬攝影機（Virtual camera）**——把一塊區域連同所有覆蓋層一起，送成一個
  網路攝影機，讓 Zoom、Teams 或 Discord 能把它選為視訊來源。需要選用的
  `pyvirtualcam` 套件與一個虛擬攝影機驅動程式（OBS 會裝一個）；少了任一項，
  按鈕會明講，而不是默默失敗。
- **讀取文字（Read text）**——拖出一塊區域，複製其中的文字、翻譯它，或
  針對它提問。這一個會把選取範圍送出這台機器；見
  [有什麼會離開這台機器](#有什麼會離開這台機器)。
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
| `F12` | 立即結束（Windows） |

媒體傳輸送的是系統媒體鍵，所以它能觸及任何會監聽這些鍵的播放器。移動視窗
時會保持它的比例，而不是把它硬切過去，後者正是 Windows 自己的
`Win+Shift+Arrow` 的做法。

遠端遙控所驅動的，就是這些相同的動作——不多不少：

- **你的手機**（Settings → Remote control）——FrontEngine 會在你的區域網路
  上提供一個小頁面；在手機上打開那個連結，按鈕就會驅動那些動作。
- **一個 MIDI 控制器**——按下 *Learn*、轉動一個旋鈕或按一個 pad，就綁定它。
  它用的是 Windows 內建的 winmm，所以不需要額外套件。旋鈕是在轉到頂端時
  觸發一次，而不是在轉的過程中反覆觸發，而且放開一個 pad 不會被算成第二次
  按下。

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
| **Read text**(Tools) | 選取的區域會送到 Anthropic 的 API | 第一次送出前會詢問一次並記住答案;可從結果視窗撤回同意。使用你自己的 `ANTHROPIC_API_KEY`,從環境變數讀取,絕不寫進任何設定檔。缺了其中任一項就什麼都不會送。 |
| **Pet chat** | 你的訊息會送到 Anthropic 的 API | 同一把金鑰、同一條規則;預設關閉。 |
| **Weather**(文字來源) | 座標會送到 Open-Meteo | 不需要金鑰、不需要帳號、沒有任何可識別身分的資料;只有你當成地點輸入的那些內容。 |
| **Phone remote** | 在你的區域網路上提供一個頁面 | 預設關閉。連結帶著一個每次啟動都會重新產生的權杖,所以舊連結會失效,而且該頁面只能請求那份固定的動作清單。它是純 HTTP:同一個網路上的其他人可以讀到權杖並按下相同的按鈕——以那些按鈕能做的事來說,這是一種困擾而非資安漏洞,但在你不信任的網路上還是別開它。 |

音訊功能只讀取一個輸出**音量計**——單一個數字——只有頻譜例外,它需要真正的
取樣來計算頻率,因此會擷取系統輸出串流。那些取樣是在記憶體裡分析的,絕不
寫到磁碟或送到任何地方,而且你一停止頻譜,擷取就立刻停止。

**外掛(Plugins)**是 Python,並以和 FrontEngine 相同的權限執行——它們無法
被沙箱隔離。載入功能預設關閉(Settings → Load plugins),每一次載入都會被
記錄,而且一個壞掉的外掛會被略過,而不是讓整個應用程式停擺。只安裝你信任的
外掛。

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
| 覆蓋層、寵物、桌布、簡報、護螢幕、擷取、錄製 | ✅ | ✅ | ✅ |
| 音訊反應、頻譜、對嘴(WASAPI) | ✅ | — | — |
| 正在播放(媒體控制) | ✅ | — | — |
| 釘住／淡出另一個視窗、視窗版面、即時複本 | ✅ | — | — |
| 把覆蓋層排除在螢幕擷取之外 | ✅ | — | — |
| MIDI 控制(winmm) | ✅ | — | — |
| 媒體傳輸鍵 | ✅ | — | — |
| 把覆蓋層釘到某個虛擬桌面 | ✅ | — | — |
| 把視窗移到下一台螢幕 | ✅ | — | — |
| `F12` 緊急離開 | ✅ | — | — |
| 把*作用中*視窗周圍調暗 | ✅ | 整個螢幕 | 整個螢幕 |
| 寵物站在其他視窗上 | ✅ | — | 需要 `wmctrl` |

在某個功能無法運作的地方,按鈕會明講,而不是默默失敗。

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
