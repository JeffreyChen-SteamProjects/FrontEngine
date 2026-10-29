from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
files = runpy.run_path(str(Path(__file__).with_name('update_focus_docs.py')))['files']
lines = {
'Eng': 'Cloning uses the selected pet’s own sprite/model, appearance, preferences and asset library, even if the settings page now selects another asset. The clone receives a new identity; later outfit or part edits do not change the original. Puppet clones also retain their source script, parameter values and active expressions.',
'Zh': '複製會使用被複製寵物本身的圖片／模型、外觀、偏好及資產庫，即使設定頁已改選其他素材也不影響。複製品使用新身分，之後換裝或換部件不會改到原寵物。Puppet 也保留來源腳本、參數值及已選表情。',
'ZhCn': '复制会使用被复制宠物本身的图片／模型、外观、偏好及资产库，即使设置页已改选其他素材也不影响。复制品使用新身份，之后换装或换部件不会改到原宠物。Puppet 也保留来源脚本、参数值及已选表情。',
'De': 'Klonen nutzt Bild/Modell, Aussehen, Einstellungen und Asset-Bibliothek des ursprünglichen Tiers, auch nach anderer Auswahl auf der Einstellungsseite. Der Klon erhält eine neue Identität; spätere Kleidungs- oder Teileänderungen betreffen das Original nicht. Puppet-Klone behalten Skript, Parameterwerte und aktive Ausdrücke.',
'Fr': 'Le clonage utilise l’image/modèle, l’apparence, les préférences et la bibliothèque de l’animal source, même après un autre choix dans les réglages. Le clone reçoit une nouvelle identité ; ses modifications ne changent pas l’original. Les clones Puppet gardent script, paramètres et expressions actives.',
'It': 'La clonazione usa immagine/modello, aspetto, preferenze e libreria dell’animale originale, anche dopo una diversa scelta nelle impostazioni. Il clone ha una nuova identità; modifiche a vestiti o parti non alterano l’originale. I cloni Puppet mantengono script, parametri ed espressioni attive.',
'Ru': 'Клонирование использует изображение/модель, внешность, настройки и библиотеку исходного питомца, независимо от нового выбора в настройках. Клон получает новую идентичность; изменение одежды или частей не меняет оригинал. Клоны Puppet сохраняют скрипт, параметры и активные выражения.',
'Es': 'Clonar usa imagen/modelo, apariencia, preferencias y biblioteca de la mascota original, aunque la página de ajustes seleccione otro recurso. El clon recibe una identidad nueva; sus cambios no afectan al original. Los clones Puppet conservan script, parámetros y expresiones activas.',
'Pt': 'Clonar usa imagem/modelo, aparência, preferências e biblioteca do pet original, mesmo que os ajustes selecionem outro recurso. O clone recebe nova identidade; mudanças não afetam o original. Clones Puppet mantêm script, parâmetros e expressões ativas.',
'Ja': '複製は設定画面の新しい選択ではなく、元のペットの画像・モデル、外観、設定、素材ライブラリを使います。新しい個体IDを持つため、その後の着替えやパーツ変更は元に影響しません。Puppetはスクリプト、パラメータ値、選択中の表情も引き継ぎます。',
'Ko': '복제는 설정 화면의 새 선택과 관계없이 원본 펫의 이미지/모델, 외형, 설정과 소재 라이브러리를 사용합니다. 새 개체 ID를 가지므로 이후 옷이나 부품 변경은 원본에 영향을 주지 않습니다. Puppet은 스크립트, 매개변수 값과 활성 표정도 유지합니다.',
}
for filename, language in files.items():
    path = root / filename
    text = path.read_text(encoding='utf-8')
    if lines[language] not in text:
        path.write_text(text.rstrip() + '\n\n' + lines[language] + '\n', encoding='utf-8', newline='\r\n')
