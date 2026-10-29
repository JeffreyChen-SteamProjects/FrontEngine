import json
from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
keys = ('pet_call_horizontal', 'pet_call_vertical', 'pet_call_offset_hint', 'pet_call_unsupported', 'pet_call_started')
labels = {
    'english': ['Left / right (px)', 'Up / down (px)', 'Negative values move left/up. The destination is limited to nearby work space; floor mode ignores vertical movement.', 'This pet does not support movement calls yet.', 'Destination placed. End interaction cancels the call.'],
    'traditional_chinese': ['左右位移（像素）', '上下位移（像素）', '負值往左／往上。落點限制在附近工作區內；地板模式忽略上下位移。', '這隻寵物尚不支援移動呼叫。', '已放置落點。選擇結束互動可取消呼叫。'],
    'simplified_chinese': ['左右位移（像素）', '上下位移（像素）', '负值往左／往上。落点限制在附近工作区内；地板模式忽略上下位移。', '这只宠物暂不支持移动呼叫。', '已放置落点。选择结束互动可取消呼叫。'],
    'germany': ['Links / rechts (px)', 'Oben / unten (px)', 'Negative Werte bewegen nach links/oben. Das Ziel bleibt im nahen Arbeitsbereich; im Bodenmodus wird die vertikale Verschiebung ignoriert.', 'Dieses Tier unterstützt noch keine Bewegungsrufe.', 'Ziel gesetzt. Interaktion beenden bricht den Ruf ab.'],
    'france': ['Gauche / droite (px)', 'Haut / bas (px)', 'Les valeurs négatives vont à gauche/en haut. La destination reste dans la zone de travail proche ; le mode sol ignore le déplacement vertical.', 'Cet animal ne prend pas encore en charge les appels de déplacement.', 'Destination placée. Terminer l’interaction annule l’appel.'],
    'italy': ['Sinistra / destra (px)', 'Su / giù (px)', 'I valori negativi spostano a sinistra/in alto. La destinazione resta nell’area di lavoro vicina; la modalità pavimento ignora lo spostamento verticale.', 'Questo animale non supporta ancora i richiami con movimento.', 'Destinazione posizionata. Termina interazione annulla il richiamo.'],
    'russian': ['Влево / вправо (пикс.)', 'Вверх / вниз (пикс.)', 'Отрицательные значения задают движение влево/вверх. Цель ограничена ближайшей рабочей областью; режим пола игнорирует вертикальное смещение.', 'Этот питомец пока не поддерживает вызов с перемещением.', 'Цель установлена. Завершение взаимодействия отменяет вызов.'],
}
for language, values in labels.items():
    path = root / 'frontengine/utils/multi_language' / (language + '.py')
    text = path.read_text(encoding='utf-8')
    for key, value in zip(keys, values):
        if repr(key) not in text:
            index = text.rfind('}')
            text = text[:index] + f'    {key!r}: ' + json.dumps(value, ensure_ascii=False) + ',\n' + text[index:]
    path.write_text(text, encoding='utf-8', newline='\n')

files = runpy.run_path(str(Path(__file__).with_name('update_puppet_petting_docs.py')))['files']
lines = {
    'Eng': 'For keyboard destination selection, choose Come here in the pet manager and enter horizontal/vertical offsets in logical pixels. Negative values mean left/up. The target is constrained to the nearby work area, and floor mode ignores vertical offsets. Perform interaction starts the call; End interaction cancels it. Busy or unsupported pets keep their current interaction.',
    'Zh': '鍵盤指定落點：在寵物管理頁選擇「過來這裡」，輸入水平／垂直位移，單位為邏輯像素，負值表示左／上。落點受附近工作區限制，地板模式忽略垂直位移。執行互動開始呼叫，結束互動取消；忙碌或不支援移動的寵物會保留目前互動。',
    'ZhCn': '键盘指定落点：在宠物管理页选择“过来这里”，输入水平／垂直位移，单位为逻辑像素，负值表示左／上。落点受附近工作区限制，地板模式忽略垂直位移。执行互动开始呼叫，结束互动取消；忙碌或不支持移动的宠物会保留当前互动。',
    'De': 'Für ein Tastaturziel wählen Sie Komm her in der Tierverwaltung und geben horizontale/vertikale Verschiebungen in logischen Pixeln ein. Negative Werte bedeuten links/oben. Das Ziel bleibt im nahen Arbeitsbereich; der Bodenmodus ignoriert vertikale Werte. Ausführen startet, Interaktion beenden bricht ab. Beschäftigte oder nicht unterstützte Tiere behalten ihre aktuelle Interaktion.',
    'Fr': 'Pour définir une destination au clavier, choisissez Viens ici dans la gestion des animaux et saisissez les décalages horizontal/vertical en pixels logiques. Les valeurs négatives signifient gauche/haut. La destination reste proche ; le mode sol ignore le décalage vertical. Exécuter lance l’appel, terminer l’interaction l’annule. Les animaux occupés ou non compatibles gardent leur interaction.',
    'It': 'Per scegliere la destinazione da tastiera, seleziona Vieni qui nella gestione animali e inserisci gli scostamenti orizzontale/verticale in pixel logici. I valori negativi indicano sinistra/alto. La meta resta vicina; la modalità pavimento ignora lo scostamento verticale. Esegui avvia il richiamo, termina interazione lo annulla. Gli animali occupati o non supportati mantengono l’interazione attuale.',
    'Ru': 'Для выбора цели с клавиатуры выберите Иди сюда в управлении питомцами и введите горизонтальное/вертикальное смещение в логических пикселях. Отрицательные значения означают влево/вверх. Цель ограничена ближайшей рабочей областью; режим пола игнорирует вертикальное смещение. Запуск действия начинает вызов, завершение отменяет его. Занятые или неподдерживаемые питомцы сохраняют текущее действие.',
    'Es': 'Para elegir destino con teclado, selecciona Ven aquí en el gestor e introduce desplazamientos horizontal/vertical en píxeles lógicos. Los negativos indican izquierda/arriba. El destino queda en el área cercana; el modo suelo ignora el desplazamiento vertical. Ejecutar inicia la llamada y finalizar interacción la cancela. Las mascotas ocupadas o no compatibles conservan su interacción.',
    'Pt': 'Para escolher o destino pelo teclado, selecione Venha aqui no gerenciador e informe deslocamentos horizontal/vertical em pixels lógicos. Valores negativos indicam esquerda/cima. O destino fica na área próxima; o modo chão ignora o deslocamento vertical. Executar inicia a chamada e encerrar interação a cancela. Pets ocupados ou incompatíveis mantêm a interação atual.',
    'Ja': 'キーボードで目的地を指定するには、管理画面で「ここに来て」を選び、水平・垂直の移動量を論理ピクセルで入力します。負数は左・上です。目的地は近くの作業領域内に制限され、床モードでは垂直移動を無視します。交流の実行で呼び出し、終了で取消します。動作中や非対応のペットの交流は維持されます。',
    'Ko': '키보드로 목적지를 정하려면 관리 화면에서 이리 와를 선택하고 수평·수직 이동량을 논리 픽셀로 입력합니다. 음수는 왼쪽·위쪽입니다. 목적지는 가까운 작업 영역으로 제한되며 바닥 모드는 수직 이동을 무시합니다. 상호작용 실행으로 호출하고 종료로 취소합니다. 바쁘거나 미지원인 펫의 기존 상호작용은 유지됩니다.',
}
for filename, language in files.items():
    path = root / filename
    text = path.read_text(encoding='utf-8')
    if lines[language] not in text:
        path.write_text(text.rstrip() + '\n\n' + lines[language] + '\n', encoding='utf-8', newline='\r\n')
