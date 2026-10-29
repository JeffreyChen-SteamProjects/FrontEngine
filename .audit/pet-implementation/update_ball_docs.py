from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
labels = {
'english': ('Throw a ball', 'Put ball away'),
'traditional_chinese': ('投出玩具球', '收起玩具球'),
'simplified_chinese': ('投出玩具球', '收起玩具球'),
'germany': ('Ball werfen', 'Ball weglegen'),
'france': ('Lancer une balle', 'Ranger la balle'),
'italy': ('Lancia una palla', 'Riponi la palla'),
'russian': ('Бросить мяч', 'Убрать мяч'),
}
for language, values in labels.items():
    path = root / 'frontengine/utils/multi_language' / (language + '.py')
    text = path.read_text(encoding='utf-8')
    if "'pet_ball_start':" not in text:
        index = text.index("    'pet_photo_title':")
        text = text[:index] + ''.join('    ' + repr(key) + ': ' + repr(value) + ',\n'
            for key, value in zip(('pet_ball_start', 'pet_ball_stop'), values)) + text[index:]
        path.write_text(text, encoding='utf-8', newline='\n')
files = runpy.run_path(str(Path(__file__).with_name('update_focus_docs.py')))['files']
lines = {
'Eng': 'Sprite pets offer Throw a ball and Put ball away. Drag and release the ball to throw it again, or right-click it to dismiss. The pet chases the bounded ball and carries it back near its starting point; a completed return grants one affection with a 30-second active-time cooldown. Work/rest, other interactions, hiding, typing-settle or timeout cancel without a reward. Puppet toys remain pending.',
'Zh': 'Sprite 寵物選單可投出或收起玩具球；拖動球再放開可重投，右鍵球可收起。寵物追球並帶回起點附近，完成往返加 1 好感，冷卻為 30 秒活躍時間。工作／休息、其他互動、隱藏、打字安靜或逾時會取消且不發獎勵。Puppet 玩具仍待完成。',
'ZhCn': 'Sprite 宠物菜单可投出或收起玩具球；拖动球再放开可重投，右键球可收起。宠物追球并带回起点附近，完成往返加 1 好感，冷却为 30 秒活跃时间。工作／休息、其他互动、隐藏、打字安静或超时会取消且不发奖励。Puppet 玩具仍待完成。',
'De': 'Sprite-Tiere können einen Ball werfen und wegräumen. Ziehen und loslassen wirft erneut, Rechtsklick entfernt ihn. Das Tier holt den begrenzten Ball zum Start zurück; Abschluss gibt 1 Zuneigung mit 30 Sekunden aktiver Abklingzeit. Arbeit/Ruhe, andere Interaktionen, Verbergen, Tippruhe oder Zeitlimit brechen ohne Belohnung ab. Puppet-Spielzeug fehlt noch.',
'Fr': 'Les Sprite peuvent lancer et ranger une balle. Glissez puis relâchez pour relancer, clic droit pour ranger. L’animal la rapporte près du départ ; le retour donne 1 affection avec 30 secondes actives de récupération. Travail/repos, autres interactions, masquage, calme pendant la saisie ou délai dépassé annulent sans récompense. Les jouets Puppet restent à faire.',
'It': 'Gli Sprite possono lanciare e riporre una palla. Trascina e rilascia per rilanciarla, clic destro per rimuoverla. L’animale la riporta vicino alla partenza; il ritorno dà 1 affetto con 30 secondi attivi di attesa. Lavoro/riposo, altre interazioni, nascondere, pausa durante la digitazione o timeout annullano senza premio. I giochi Puppet restano da fare.',
'Ru': 'Sprite могут бросить и убрать мяч. Перетащите и отпустите для нового броска, правый щелчок убирает мяч. Питомец возвращает его к началу; завершение даёт 1 привязанности с задержкой 30 активных секунд. Работа/отдых, другие действия, скрытие, покой при наборе или тайм-аут отменяют игру без награды. Игрушки Puppet ещё не готовы.',
'Es': 'Los Sprite pueden lanzar y guardar una pelota. Arrastra y suelta para relanzar; clic derecho para guardar. La mascota la devuelve al inicio y gana 1 afecto con 30 segundos activos de espera. Trabajo/descanso, otras acciones, ocultar, pausa al escribir o tiempo agotado cancelan sin premio. Los juguetes Puppet siguen pendientes.',
'Pt': 'Os Sprite podem lançar e guardar uma bola. Arraste e solte para relançar; botão direito para guardar. O pet a devolve ao início e ganha 1 afeto com 30 segundos ativos de intervalo. Trabalho/descanso, outras ações, ocultar, pausa ao digitar ou timeout cancelam sem prêmio. Brinquedos Puppet ainda estão pendentes.',
'Ja': 'Spriteはボールを投げて片付けられます。ドラッグして放すと再投球、右クリックで終了します。開始地点付近まで持ち帰ると好感度1、クールダウンは活動時間30秒です。仕事・休息、他の交流、非表示、入力中の静止、時間切れでは報酬なしで終了します。Puppetの玩具は未完成です。',
'Ko': 'Sprite는 공을 던지고 치울 수 있습니다. 드래그 후 놓으면 다시 던지고 오른쪽 클릭하면 치웁니다. 시작 지점 근처로 가져오면 호감도 1을 주며 대기 시간은 활동 시간 30초입니다. 작업/휴식, 다른 상호작용, 숨김, 입력 중 정지 또는 시간 초과는 보상 없이 취소합니다. Puppet 장난감은 아직 미완성입니다.',
}
for filename, language in files.items():
    path = root / filename
    text = path.read_text(encoding='utf-8')
    if lines[language] not in text:
        path.write_text(text.rstrip() + '\n\n' + lines[language] + '\n', encoding='utf-8', newline='\r\n')
