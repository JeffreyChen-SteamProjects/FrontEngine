import json
from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
labels = {
    'english': ['Come here', 'Drag the marker to a nearby destination. Right-click to cancel.'],
    'traditional_chinese': ['過來這裡', '拖動標記指定附近落點，右鍵取消。'],
    'simplified_chinese': ['过来这里', '拖动标记指定附近落点，右键取消。'],
    'germany': ['Komm her', 'Ziehen Sie die Markierung zu einem nahen Ziel. Rechtsklick bricht ab.'],
    'france': ['Viens ici', 'Déplacez le repère vers une destination proche. Clic droit pour annuler.'],
    'italy': ['Vieni qui', 'Trascina il segnaposto verso una destinazione vicina. Clic destro per annullare.'],
    'russian': ['Иди сюда', 'Перетащите метку в ближайшую точку. Правая кнопка отменяет команду.'],
}
for language, values in labels.items():
    path = root / 'frontengine/utils/multi_language' / (language + '.py')
    text = path.read_text(encoding='utf-8')
    for key, value in zip(('pet_come', 'pet_come_hint'), values):
        if repr(key) not in text:
            index = text.rfind('}')
            text = text[:index] + f'    {key!r}: ' + json.dumps(value, ensure_ascii=False) + ',\n' + text[index:]
    path.write_text(text, encoding='utf-8', newline='\n')

files = runpy.run_path(str(Path(__file__).with_name('update_puppet_petting_docs.py')))['files']
lines = {
    'Eng': 'Sprite pets offer Come here with a draggable nearby marker. Floor pets approach along the floor; wander/chase pets follow in two dimensions. Arrival triggers a short greeting with the normal greeting cooldown. Right-click the marker or End interaction to cancel. Work/rest, hiding, feeding or a new toy also cancel.',
    'Zh': 'Sprite 寵物可用「過來這裡」顯示可拖動的附近落點標記。地板模式沿地面前往，自由漫遊／追游標模式可沿兩軸移動；抵達後短招呼，沿用招呼冷卻。標記右鍵或結束互動可取消；工作／休息、隱藏、餵食或換玩具也會取消。',
    'ZhCn': 'Sprite 宠物可用「过来这里」显示可拖动的附近落点标记。地板模式沿地面前往，自由漫游／追光标模式可沿两轴移动；抵达后短招呼，沿用招呼冷却。标记右键或结束互动可取消；工作／休息、隐藏、喂食或换玩具也会取消。',
    'De': 'Sprite-Tiere können mit Komm her einer nahen verschiebbaren Markierung folgen. Bodenmodus bleibt am Boden; freie Modi bewegen sich zweidimensional. Ankunft startet einen kurzen Gruß mit normaler Wartezeit. Rechtsklick oder Interaktion beenden bricht ab, ebenso Arbeit/Ruhe, Ausblenden, Füttern oder ein neues Spielzeug.',
    'Fr': 'Les animaux Sprite suivent un repère proche déplaçable avec Viens ici. Le mode sol reste au sol ; les modes libres se déplacent sur deux axes. L’arrivée déclenche une salutation avec son délai habituel. Clic droit ou Fin de l’interaction annule, comme travail/repos, masquage, repas ou nouveau jouet.',
    'It': 'Gli animali Sprite seguono un segnaposto vicino trascinabile con Vieni qui. Il modo pavimento resta a terra; i modi liberi si muovono su due assi. L’arrivo avvia un saluto con l’attesa normale. Clic destro o Fine interazione annulla, così come lavoro/riposo, nascondimento, cibo o un nuovo gioco.',
    'Ru': 'Команда Иди сюда ведёт Sprite к перемещаемой ближайшей метке. Напольный режим движется по полу, свободные режимы по двум осям. По прибытии выполняется приветствие с обычной задержкой. Правая кнопка или завершение взаимодействия отменяет команду, как и работа/отдых, скрытие, кормление или новая игрушка.',
    'Es': 'Ven aquí permite a Sprite seguir un marcador cercano arrastrable. El modo suelo sigue el suelo y los modos libres usan dos ejes. Al llegar saluda con la espera habitual. Clic derecho o Finalizar interacción cancela, igual que trabajo/reposo, ocultar, alimentar o cambiar de juguete.',
    'Pt': 'Vem aqui faz o Sprite seguir um marcador próximo arrastável. O modo chão segue o piso e os modos livres usam dois eixos. Ao chegar, cumprimenta com a espera normal. Clique direito ou Encerrar interação cancela, assim como trabalho/descanso, ocultar, alimentar ou trocar brinquedo.',
    'Ja': 'Spriteの「ここに来て」で近くの目標マーカーをドラッグできます。床モードは床沿い、自由移動モードは2軸で進みます。到着後は通常の待機時間を共有する短い挨拶をします。右クリックや交流終了で取消可能で、仕事・休息、非表示、餌やり、別のおもちゃでも終了します。',
    'Ko': 'Sprite의 이리 와 명령은 드래그 가능한 가까운 목표 표시를 만듭니다. 바닥 모드는 바닥을 따라, 자유 이동 모드는 두 축으로 이동합니다. 도착하면 기존 대기 시간을 공유하는 짧은 인사를 합니다. 우클릭이나 상호작용 종료로 취소하며 작업·휴식, 숨김, 먹이 주기, 다른 장난감도 취소합니다.',
}
for filename, lang in files.items():
    path = root / filename
    text = path.read_text(encoding='utf-8')
    if lines[lang] not in text:
        path.write_text(text.rstrip() + '\n\n' + lines[lang] + '\n', encoding='utf-8', newline='\r\n')
