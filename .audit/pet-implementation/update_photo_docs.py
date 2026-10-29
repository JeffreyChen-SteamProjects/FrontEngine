from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
keys = ('title', 'hint', 'current', 'pose', 'time', 'save', 'failed', 'saved')
labels = {
'english': ('Pet photo', 'Only the pet is saved, with a transparent background.', 'Captured pose', 'Pose', 'Pose time', 'Save transparent PNG', 'Could not save. Choose another location and retry.', 'Photo saved'),
'traditional_chinese': ('寵物拍照', '只保存寵物本身，背景透明。', '拍攝時的姿勢', '姿勢', '姿勢時間', '保存透明 PNG', '無法保存，請選擇其他位置重試。', '照片已保存'),
'simplified_chinese': ('宠物拍照', '只保存宠物本身，背景透明。', '拍摄时的姿势', '姿势', '姿势时间', '保存透明 PNG', '无法保存，请选择其他位置重试。', '照片已保存'),
'germany': ('Tierfoto', 'Nur das Tier wird mit transparentem Hintergrund gespeichert.', 'Aufgenommene Pose', 'Pose', 'Posenzeit', 'Transparentes PNG speichern', 'Speichern fehlgeschlagen. Anderen Ort wählen und erneut versuchen.', 'Foto gespeichert'),
'france': ('Photo de l’animal', 'Seul l’animal est enregistré, sur fond transparent.', 'Pose capturée', 'Pose', 'Temps de pose', 'Enregistrer un PNG transparent', 'Échec de l’enregistrement. Choisissez un autre emplacement.', 'Photo enregistrée'),
'italy': ('Foto dell’animale', 'Viene salvato solo l’animale, con sfondo trasparente.', 'Posa acquisita', 'Posa', 'Tempo della posa', 'Salva PNG trasparente', 'Salvataggio non riuscito. Scegli un’altra posizione.', 'Foto salvata'),
'russian': ('Фото питомца', 'Сохраняется только питомец с прозрачным фоном.', 'Снятая поза', 'Поза', 'Время позы', 'Сохранить прозрачный PNG', 'Не удалось сохранить. Выберите другое место и повторите.', 'Фото сохранено'),
}
for language, values in labels.items():
    path = root / 'frontengine/utils/multi_language' / (language + '.py')
    text = path.read_text(encoding='utf-8')
    if "'pet_photo_title':" not in text:
        index = text.index("    'pet_wardrobe_region':")
        text = text[:index] + ''.join('    ' + repr('pet_photo_' + key) + ': ' + repr(value) + ',\n'
                                    for key, value in zip(keys, values)) + text[index:]
        path.write_text(text, encoding='utf-8', newline='\n')
files = runpy.run_path(str(Path(__file__).with_name('update_focus_docs.py')))['files']
lines = {
'Eng': 'The sprite pet menu offers Pet photo: freeze its current appearance or select an authored layered pose, then save a transparent PNG. Captures contain only the pet, without desktop pixels or speech bubbles. Puppet photography is not yet supported.',
'Zh': 'Sprite 寵物選單提供「寵物拍照」：凍結目前外觀，或選擇分層素材已有的姿勢，再保存透明 PNG。只輸出寵物，不含桌面像素與對話泡泡。Puppet 拍照尚未支援。',
'ZhCn': 'Sprite 宠物菜单提供“宠物拍照”：冻结当前外观，或选择分层素材已有的姿势，再保存透明 PNG。只输出宠物，不含桌面像素与对话气泡。Puppet 拍照尚未支持。',
'De': 'Das Sprite-Tiermenü bietet Tierfoto: aktuelle Ansicht einfrieren oder eine vorhandene Ebenenpose wählen und als transparentes PNG speichern. Desktop und Sprechblasen werden nicht aufgenommen. Puppet-Fotos werden noch nicht unterstützt.',
'Fr': 'Le menu des animaux Sprite propose une photo : figer l’apparence actuelle ou choisir une pose en calques, puis enregistrer un PNG transparent. Aucun pixel du bureau ni bulle de dialogue n’est inclus. Les photos Puppet ne sont pas encore prises en charge.',
'It': 'Il menu Sprite offre una foto: congela l’aspetto attuale o scegli una posa a livelli e salva un PNG trasparente. Desktop e fumetti sono esclusi. Le foto Puppet non sono ancora supportate.',
'Ru': 'Меню Sprite предлагает фото: зафиксировать текущий вид или выбрать готовую послойную позу и сохранить прозрачный PNG. Рабочий стол и реплики не попадают в кадр. Фото Puppet пока не поддерживается.',
'Es': 'El menú Sprite permite fotografiar la apariencia actual o elegir una pose por capas y guardar un PNG transparente. No incluye el escritorio ni bocadillos. Las fotos Puppet aún no están disponibles.',
'Pt': 'O menu Sprite permite fotografar a aparência atual ou escolher uma pose em camadas e salvar um PNG transparente. A área de trabalho e os balões ficam de fora. Fotos Puppet ainda não são suportadas.',
'Ja': 'Spriteのメニューで現在の姿を撮影するか、レイヤー素材のポーズを選び、透過PNGを保存できます。デスクトップや吹き出しは含みません。Puppetの撮影は未対応です。',
'Ko': 'Sprite 메뉴에서 현재 모습을 촬영하거나 레이어 소재의 포즈를 골라 투명 PNG로 저장할 수 있습니다. 바탕 화면과 말풍선은 포함하지 않습니다. Puppet 촬영은 아직 지원하지 않습니다.',
}
for filename, language in files.items():
    path = root / filename
    text = path.read_text(encoding='utf-8')
    if lines[language] not in text:
        path.write_text(text.rstrip() + '\n\n' + lines[language] + '\n', encoding='utf-8', newline='\r\n')
