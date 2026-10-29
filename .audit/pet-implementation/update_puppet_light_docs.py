import json
from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
labels = {
    'english': ['Drag the light spot; release near the pet to play. Right-click to cancel.', 'Light placed. End interaction puts it away.'],
    'traditional_chinese': ['拖動光點，在寵物附近放開即可玩耍；右鍵取消。', '已放置光點。選擇結束互動可收起。'],
    'simplified_chinese': ['拖动光点，在宠物附近松开即可玩耍；右键取消。', '已放置光点。选择结束互动可收起。'],
    'germany': ['Lichtpunkt ziehen und nahe beim Tier loslassen, um zu spielen. Rechtsklick bricht ab.', 'Lichtpunkt gesetzt. Interaktion beenden entfernt ihn.'],
    'france': ['Déplacez le point lumineux et relâchez-le près de l’animal pour jouer. Clic droit pour annuler.', 'Point lumineux placé. Terminer l’interaction le retire.'],
    'italy': ['Trascina il punto luminoso e rilascialo vicino all’animale per giocare. Clic destro per annullare.', 'Punto luminoso posizionato. Termina interazione lo rimuove.'],
    'russian': ['Перетащите световую точку и отпустите рядом с питомцем для игры. Правая кнопка отменяет.', 'Световая точка установлена. Завершение взаимодействия убирает её.'],
}
for language, values in labels.items():
    path = root / 'frontengine/utils/multi_language' / (language + '.py')
    text = path.read_text(encoding='utf-8')
    for key, value in zip(('pet_light_hint', 'pet_light_started'), values):
        if repr(key) not in text:
            index = text.rfind('}')
            text = text[:index] + f'    {key!r}: ' + json.dumps(value, ensure_ascii=False) + ',\n' + text[index:]
    path.write_text(text, encoding='utf-8', newline='\n')
files = runpy.run_path(str(Path(__file__).with_name('update_puppet_petting_docs.py')))['files']
lines = {
    'Eng': 'Puppet can chase a draggable light spot from its menu. Both Sprite and Puppet managers offer light play with keyboard offsets. Releasing the light near the pet for half a second starts the shared three-second play action; affection is awarded only on completion and follows the normal cooldown. Calls and light play share one target. Put toy away, End interaction, care, manual dragging, mode changes or hiding cancel it.',
    'Zh': 'Puppet 選單可開始追逐可拖動的光點；Sprite 與 Puppet 都能在管理頁用鍵盤位移放置光點。光點在寵物附近放開半秒後，開始共用的三秒玩耍，完成才增加好感並沿用冷卻。呼叫與光點共用單一目標；收起玩具、結束互動、照顧、手動拖曳、模式切換或隱藏可取消。',
    'ZhCn': 'Puppet 菜单可开始追逐可拖动的光点；Sprite 和 Puppet 都能在管理页用键盘位移放置光点。光点在宠物附近松开半秒后，开始共用的三秒玩耍，完成才增加好感并沿用冷却。呼叫与光点共用单一目标；收起玩具、结束互动、照护、手动拖动、模式切换或隐藏可取消。',
    'De': 'Puppet kann über sein Menü einem ziehbaren Lichtpunkt folgen. Im Manager bieten Sprite und Puppet Lichtspiel mit Tastaturversatz. Nach einer halben Sekunde losgelassen in der Nähe beginnt das gemeinsame dreisekündige Spiel; Zuneigung gibt es erst nach Abschluss mit normaler Wartezeit. Ruf und Licht teilen ein Ziel. Spielzeug weglegen, Interaktion beenden, Pflege, Ziehen, Moduswechsel oder Ausblenden brechen ab.',
    'Fr': 'Puppet peut poursuivre un point lumineux déplaçable depuis son menu. Le gestionnaire permet à Sprite et Puppet de placer ce point au clavier. Relâché près de l’animal pendant une demi-seconde, il lance le jeu commun de trois secondes ; l’affection arrive seulement à la fin, avec le délai normal. Appel et lumière partagent une cible. Ranger, terminer, soigner, déplacer manuellement, changer de mode ou masquer annule.',
    'It': 'Puppet può inseguire un punto luminoso trascinabile dal menu. Il gestore permette a Sprite e Puppet di posizionarlo da tastiera. Rilasciato vicino all’animale per mezzo secondo avvia il gioco comune di tre secondi; l’affetto arriva solo al termine, con l’attesa normale. Richiamo e luce condividono una meta. Riporre, terminare, curare, trascinare, cambiare modalità o nascondere annulla.',
    'Ru': 'Puppet может преследовать перемещаемую световую точку через меню. Менеджер позволяет Sprite и Puppet задавать её положение с клавиатуры. Отпущенная рядом на полсекунды точка запускает общую трёхсекундную игру; привязанность начисляется только после завершения с обычной задержкой. Вызов и свет используют одну цель. Уборка игрушки, завершение, уход, перетаскивание, смена режима или скрытие отменяют действие.',
    'Es': 'Puppet puede perseguir un punto de luz arrastrable desde el menú. El gestor permite a Sprite y Puppet colocarlo con teclado. Soltarlo cerca durante medio segundo inicia el juego compartido de tres segundos; el afecto llega solo al completar, con la espera habitual. Llamada y luz comparten un objetivo. Guardar, finalizar, cuidar, arrastrar, cambiar modo u ocultar cancela.',
    'Pt': 'Puppet pode perseguir um ponto de luz arrastável pelo menu. O gerenciador permite a Sprite e Puppet posicioná-lo pelo teclado. Soltá-lo perto por meio segundo inicia a brincadeira compartilhada de três segundos; o afeto chega apenas ao concluir, com a espera normal. Chamada e luz usam um alvo. Guardar, encerrar, cuidar, arrastar, mudar modo ou ocultar cancela.',
    'Ja': 'Puppetのメニューからドラッグ可能な光点を追いかけられます。SpriteとPuppetの管理画面ではキーボード移動量で光点を配置できます。近くで放して半秒後に共通の3秒間の遊びが始まり、完了時だけ通常の待機時間に従って好感度が増えます。呼び出しと光点は一つの目標を共有します。片付け、交流終了、世話、ドラッグ、モード変更、非表示で取り消します。',
    'Ko': 'Puppet 메뉴에서 드래그 가능한 광점을 쫓을 수 있습니다. Sprite와 Puppet 관리 화면에서는 키보드 이동량으로 광점을 배치합니다. 가까이에서 놓고 반 초가 지나면 공통 3초 놀이를 시작하며 완료 후에만 일반 대기 규칙에 따라 호감도가 증가합니다. 호출과 광점은 하나의 목표를 공유합니다. 치우기, 종료, 돌봄, 드래그, 모드 변경, 숨김으로 취소합니다.',
}
for filename, language in files.items():
    path = root / filename
    text = path.read_text(encoding='utf-8')
    if lines[language] not in text:
        path.write_text(text.rstrip() + '\n\n' + lines[language] + '\n', encoding='utf-8', newline='\r\n')
