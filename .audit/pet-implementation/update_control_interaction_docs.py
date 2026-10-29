import json
from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
labels = {
    'english': ['Interaction', 'Perform interaction', 'Start or show this pet before interacting.'],
    'traditional_chinese': ['互動', '執行互動', '請先啟動或顯示這隻寵物，再進行互動。'],
    'simplified_chinese': ['互动', '执行互动', '请先启动或显示这只宠物，再进行互动。'],
    'germany': ['Interaktion', 'Interaktion ausführen', 'Starten oder zeigen Sie dieses Tier vor der Interaktion.'],
    'france': ['Interaction', 'Effectuer l’interaction', 'Démarrez ou affichez cet animal avant d’interagir.'],
    'italy': ['Interazione', 'Esegui interazione', 'Avvia o mostra questo animale prima di interagire.'],
    'russian': ['Взаимодействие', 'Выполнить действие', 'Сначала запустите или покажите этого питомца.'],
}
for language, values in labels.items():
    path = root / 'frontengine/utils/multi_language' / (language + '.py')
    text = path.read_text(encoding='utf-8')
    for key, value in zip(('pet_interact_label', 'pet_interact_run', 'pet_interact_unavailable'), values):
        if repr(key) not in text:
            index = text.rfind('}')
            text = text[:index] + f'    {key!r}: ' + json.dumps(value, ensure_ascii=False) + ',\n' + text[index:]
    path.write_text(text, encoding='utf-8', newline='\n')

files = runpy.run_path(str(Path(__file__).with_name('update_puppet_petting_docs.py')))['files']
lines = {
    'Eng': 'Pet identities now provides an Interaction picker and Perform interaction button for the selected live pet. Keyboard users can greet, pet briefly, groom, choose treats, change play/work/rest mode or cancel. Manager petting uses the same timed care rules without pointer strokes. Hidden or inactive pets show feedback instead of spawning.',
    'Zh': '寵物身分區新增互動清單與執行按鈕，可用鍵盤對選定的運作中寵物招呼、短撫摸、梳理、餵點心、切換玩耍／工作／休息或取消。管理頁撫摸沿用計時照護規則，不需滑鼠手勢；隱藏或未啟動時只顯示提示，不自行召喚。',
    'ZhCn': '宠物身份区新增互动列表与执行按钮，可用键盘对选中的运行中宠物招呼、短抚摸、梳理、喂点心、切换玩耍／工作／休息或取消。管理页抚摸沿用计时照护规则，不需鼠标手势；隐藏或未启动时只显示提示，不自行召唤。',
    'De': 'Der Identitätsbereich bietet eine Interaktionsauswahl und Ausführen für das gewählte aktive Tier. Per Tastatur sind Gruß, kurzes Streicheln, Pflege, Leckerbissen, Spiel/Arbeit/Ruhe und Abbruch möglich. Streicheln nutzt die gemeinsame Zeitregel ohne Zeigergesten. Verborgene oder inaktive Tiere werden nicht gestartet.',
    'Fr': 'La zone des identités propose une liste d’interactions et un bouton pour l’animal actif sélectionné. Le clavier permet salut, courte caresse, toilettage, friandises, jeu/travail/repos ou annulation. La caresse utilise les règles temporisées sans geste du pointeur. Un animal masqué ou inactif n’est pas lancé.',
    'It': 'La sezione identità offre scelta ed esecuzione delle interazioni per l’animale attivo selezionato. Da tastiera sono disponibili saluto, breve carezza, cura, spuntini, gioco/lavoro/riposo e annullamento. La carezza usa le regole temporizzate senza gesti del puntatore. Animali nascosti o inattivi non vengono avviati.',
    'Ru': 'В разделе питомцев появились выбор и запуск действия для выбранного активного питомца. Клавиатурой доступны приветствие, короткое поглаживание, уход, угощения, игра/работа/отдых и отмена. Поглаживание использует общий таймер без движений указателя. Скрытые и неактивные питомцы автоматически не запускаются.',
    'Es': 'La sección de identidades permite elegir y ejecutar interacciones para la mascota activa seleccionada. Con teclado se puede saludar, acariciar brevemente, asear, dar golosinas, cambiar juego/trabajo/descanso o cancelar. La caricia usa las reglas temporizadas sin gestos del puntero. No inicia mascotas ocultas o inactivas.',
    'Pt': 'A seção de identidades permite escolher e executar interações no pet ativo selecionado. Pelo teclado é possível cumprimentar, acariciar brevemente, cuidar, dar petiscos, mudar brincar/trabalhar/descansar ou cancelar. O carinho usa as regras temporizadas sem gestos do ponteiro. Pets ocultos ou inativos não são iniciados.',
    'Ja': '個体管理に交流の選択と実行ボタンを追加しました。選択した起動中のペットへ、キーボードで挨拶、短い撫でる動作、手入れ、おやつ、遊び・仕事・休息の切替、取消ができます。管理画面の撫でる操作はポインター不要の共通時間ルールを使います。非表示や未起動の個体を自動起動しません。',
    'Ko': '개체 관리에서 선택한 실행 중 펫의 상호작용을 고르고 실행할 수 있습니다. 키보드로 인사, 짧은 쓰다듬기, 손질, 간식, 놀이·작업·휴식 전환 및 취소를 지원합니다. 관리 화면의 쓰다듬기는 포인터 동작 없이 공통 시간 규칙을 사용합니다. 숨김 또는 비활성 펫을 자동 실행하지 않습니다.',
}
for filename, lang in files.items():
    path = root / filename
    text = path.read_text(encoding='utf-8')
    if lines[lang] not in text:
        path.write_text(text.rstrip() + '\n\n' + lines[lang] + '\n', encoding='utf-8', newline='\r\n')
