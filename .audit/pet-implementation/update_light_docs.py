from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
labels = {
'english': ('Play with a light spot', 'Put toy away'),
'traditional_chinese': ('光點逗逗牠', '收起玩具'),
'simplified_chinese': ('光点逗逗它', '收起玩具'),
'germany': ('Mit Lichtpunkt spielen', 'Spielzeug weglegen'),
'france': ('Jouer avec un point lumineux', 'Ranger le jouet'),
'italy': ('Gioca con un punto luminoso', 'Riponi il giocattolo'),
'russian': ('Играть со световой точкой', 'Убрать игрушку'),
}
for language, values in labels.items():
    path = root / 'frontengine/utils/multi_language' / (language + '.py')
    text = path.read_text(encoding='utf-8')
    if "'pet_light_start':" not in text:
        index = text.index("    'pet_photo_title':")
        text = text[:index] + ''.join('    ' + repr(key) + ': ' + repr(value) + ',\n'
            for key, value in zip(('pet_light_start', 'pet_toy_stop'), values)) + text[index:]
        path.write_text(text, encoding='utf-8', newline='\n')
files = runpy.run_path(str(Path(__file__).with_name('update_focus_docs.py')))['files']
lines = {
'Eng': 'Play with a light spot adds a small draggable target near the pet. Its range is bounded; floor pets chase along the floor. Release the target and let the pet reach it to start a short play reaction, rewarded only on completion under the existing play cooldown. Right-click the spot or choose Put toy away to stop. Only one ball or light toy can be active per pet.',
'Zh': '「光點逗逗牠」在寵物附近放置可拖動的小光點，活動距離有限；地板寵物沿地面追逐。放開光點並讓寵物追到後開始短暫玩耍，完成才依既有玩耍冷卻給獎勵。右鍵光點或選「收起玩具」可停止。同一隻寵物一次只能使用球或光點其中一個。',
'ZhCn': '“光点逗逗它”在宠物附近放置可拖动的小光点，活动距离有限；地板宠物沿地面追逐。放开光点并让宠物追到后开始短暂玩耍，完成才按既有玩耍冷却给奖励。右键光点或选“收起玩具”可停止。同一只宠物一次只能使用球或光点其中一个。',
'De': 'Der Lichtpunkt ist ein kleiner ziehbarer Zielpunkt in begrenzter Nähe des Tiers. Bodentiere folgen am Boden. Nach Loslassen und Erreichen beginnt eine kurze Spielreaktion, belohnt erst nach Abschluss mit der bestehenden Abklingzeit. Rechtsklick oder Spielzeug weglegen beendet sie. Pro Tier ist nur ein Ball oder Lichtpunkt aktiv.',
'Fr': 'Le point lumineux est une petite cible déplaçable à portée limitée. Les animaux au sol suivent au sol. Relâchez la cible et laissez l’animal l’atteindre pour lancer une courte réaction de jeu, récompensée après achèvement selon le délai existant. Clic droit ou Ranger termine. Une seule balle ou lumière par animal.',
'It': 'Il punto luminoso è un piccolo bersaglio trascinabile a distanza limitata. Gli animali a terra lo seguono sul pavimento. Rilascia il bersaglio e lascia che venga raggiunto per avviare una breve reazione, premiata al completamento con l’attesa esistente. Clic destro o Riponi termina. Un solo giocattolo per animale.',
'Ru': 'Световая точка — небольшая перетаскиваемая цель с ограниченной дальностью. Наземные питомцы следуют по полу. Отпустите цель: достигнув её, питомец начнёт короткую игру, награда выдаётся после завершения с обычной задержкой. Правый щелчок или Убрать завершает игру. На питомца доступна одна игрушка за раз.',
'Es': 'El punto de luz es un objetivo pequeño que se arrastra dentro de una distancia limitada. Las mascotas de suelo lo siguen por el suelo. Suéltalo y deja que lo alcancen para iniciar una breve reacción, premiada al completarse con la espera habitual. Clic derecho o Guardar termina. Solo un juguete por mascota.',
'Pt': 'O ponto de luz é um alvo pequeno arrastável a uma distância limitada. Pets de chão o seguem pelo chão. Solte o alvo e deixe o pet alcançá-lo para iniciar uma reação curta, premiada ao terminar com o intervalo habitual. Botão direito ou Guardar encerra. Apenas um brinquedo por pet.',
'Ja': '光点は近くでドラッグできる小さな標的です。距離は制限され、床モードでは床を追います。放した光点に到着すると短い遊びが始まり、完了時だけ既存のクールダウンに従って報酬を得ます。右クリックか玩具を片付ける操作で終了します。各ペットの玩具は同時に1個です。',
'Ko': '빛점은 가까운 범위에서 드래그할 수 있는 작은 목표입니다. 바닥 모드는 바닥을 따라갑니다. 놓은 빛점에 도착하면 짧은 놀이가 시작되고 완료 시 기존 대기 시간에 따라 보상을 줍니다. 오른쪽 클릭이나 장난감 치우기로 종료합니다. 펫마다 한 번에 하나의 장난감만 사용합니다.',
}
for filename, language in files.items():
    path = root / filename
    text = path.read_text(encoding='utf-8')
    if lines[language] not in text:
        path.write_text(text.rstrip() + '\n\n' + lines[language] + '\n', encoding='utf-8', newline='\r\n')
