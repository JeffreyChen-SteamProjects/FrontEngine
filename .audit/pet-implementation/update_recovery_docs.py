from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
keys = ('pet_recover', 'pet_recover_inactive', 'pet_recover_failed', 'pet_recover_done')
labels = {
'english': ('Bring pet back', 'This pet is not active. Start it first.', 'Could not bring the pet back. Check the screen and reduce the pet size if needed.', 'Pet returned to the selected screen.'),
'traditional_chinese': ('找回寵物', '這隻寵物尚未啟用，請先啟動。', '無法找回，請確認螢幕，必要時縮小寵物尺寸。', '寵物已回到目標螢幕。'),
'simplified_chinese': ('找回宠物', '这只宠物尚未启用，请先启动。', '无法找回，请确认屏幕，必要时缩小宠物尺寸。', '宠物已回到目标屏幕。'),
'germany': ('Tier zurückholen', 'Dieses Tier ist nicht aktiv. Zuerst starten.', 'Rückholen fehlgeschlagen. Bildschirm prüfen und Tier gegebenenfalls verkleinern.', 'Tier ist auf dem gewählten Bildschirm.'),
'france': ('Ramener l’animal', 'Cet animal est inactif. Démarrez-le d’abord.', 'Impossible de ramener l’animal. Vérifiez l’écran et réduisez sa taille si nécessaire.', 'Animal ramené sur l’écran choisi.'),
'italy': ('Riporta l’animale', 'Questo animale non è attivo. Avvialo prima.', 'Impossibile riportarlo. Controlla lo schermo e riduci le dimensioni se necessario.', 'Animale riportato sullo schermo scelto.'),
'russian': ('Вернуть питомца', 'Питомец не активен. Сначала запустите его.', 'Не удалось вернуть. Проверьте экран и при необходимости уменьшите питомца.', 'Питомец возвращён на выбранный экран.'),
}
for language, values in labels.items():
    path = root / 'frontengine/utils/multi_language' / (language + '.py')
    text = path.read_text(encoding='utf-8')
    if "'pet_recover':" not in text:
        index = text.index("    'pet_photo_title':")
        text = text[:index] + ''.join('    ' + repr(key) + ': ' + repr(value) + ',\n'
                                    for key, value in zip(keys, values)) + text[index:]
        path.write_text(text, encoding='utf-8', newline='\n')
files = runpy.run_path(str(Path(__file__).with_name('update_focus_docs.py')))['files']
lines = {
'Eng': 'Select an active identity and choose Bring pet back to move it into the selected monitor’s work area. Hidden pets become visible, unfinished interactions and toys stop, and sprite physics bounds follow the new screen. Appearance and care values remain unchanged. Inactive pets require Start; oversized pets require a smaller size first.',
'Zh': '選擇已啟用的個體後按「找回寵物」，可帶回目標螢幕工作區。隱藏寵物會重新顯示，未完成互動與玩具會停止，Sprite 移動邊界同步更新；外觀與養成數值不變。未啟用者須先啟動，尺寸超過工作區者須先縮小。',
'ZhCn': '选择已启用的个体后按“找回宠物”，可带回目标屏幕工作区。隐藏宠物会重新显示，未完成互动与玩具会停止，Sprite 移动边界同步更新；外观与养成数值不变。未启用者须先启动，尺寸超过工作区者须先缩小。',
'De': 'Aktive Identität wählen und Tier zurückholen bringt sie in den Arbeitsbereich des Zielbildschirms. Verborgene Tiere werden sichtbar, offene Interaktionen und Spielzeuge enden, Sprite-Grenzen folgen dem Bildschirm. Aussehen und Pflegewerte bleiben erhalten. Inaktive Tiere zuerst starten, zu große zuerst verkleinern.',
'Fr': 'Sélectionnez une identité active puis Ramener l’animal pour le placer dans la zone utile de l’écran choisi. Les animaux cachés réapparaissent, interactions inachevées et jouets s’arrêtent, les limites Sprite suivent l’écran. Apparence et valeurs restent intactes. Démarrez les inactifs et réduisez les trop grands.',
'It': 'Seleziona un’identità attiva e Riporta l’animale per spostarla nell’area utile dello schermo scelto. Gli animali nascosti riappaiono, interazioni incomplete e giocattoli si fermano, i limiti Sprite seguono lo schermo. Aspetto e valori restano invariati. Avvia gli inattivi e riduci quelli troppo grandi.',
'Ru': 'Выберите активного питомца и Вернуть питомца, чтобы переместить его в рабочую область выбранного экрана. Скрытые появляются, незаконченные действия и игрушки прекращаются, границы Sprite обновляются. Внешность и показатели сохраняются. Неактивных сначала запустите, слишком больших уменьшите.',
'Es': 'Selecciona una identidad activa y Traer mascota para moverla al área útil del monitor elegido. Las ocultas reaparecen, acciones incompletas y juguetes se detienen y los límites Sprite se actualizan. Apariencia y valores no cambian. Inicia las inactivas y reduce las demasiado grandes.',
'Pt': 'Selecione uma identidade ativa e Trazer pet para movê-la à área útil do monitor escolhido. Pets ocultos reaparecem, ações incompletas e brinquedos param e os limites Sprite são atualizados. Aparência e valores não mudam. Inicie os inativos e reduza os grandes demais.',
'Ja': '起動中の個体を選び、ペットを戻す操作で指定画面の作業領域へ移動できます。非表示のペットも表示し、未完了の交流や玩具を終了してSpriteの移動範囲を更新します。外観と育成値は維持します。未起動なら先に起動し、大きすぎる場合は縮小してください。',
'Ko': '활성 개체를 선택하고 펫 되찾기를 누르면 선택한 화면의 작업 영역으로 옮깁니다. 숨긴 펫을 표시하고 미완료 상호작용과 장난감을 끝내며 Sprite 이동 범위를 갱신합니다. 외형과 성장 값은 유지합니다. 비활성 펫은 먼저 시작하고 너무 큰 펫은 줄여 주세요.',
}
for filename, language in files.items():
    path = root / filename
    text = path.read_text(encoding='utf-8')
    if lines[language] not in text:
        path.write_text(text.rstrip() + '\n\n' + lines[language] + '\n', encoding='utf-8', newline='\r\n')
