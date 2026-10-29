from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
files = runpy.run_path(str(Path(__file__).with_name('update_puppet_petting_docs.py')))['files']
old = {
    'Eng': ' Puppet movement is not implemented.',
    'Zh': 'Puppet 移動尚未實作。',
    'ZhCn': 'Puppet 移动尚未实现。',
    'De': ' Puppet-Bewegung fehlt noch.',
    'Fr': ' Le déplacement Puppet reste à faire.',
    'It': ' Il movimento Puppet non è implementato.',
    'Ru': ' Движение Puppet пока не реализовано.',
    'Es': ' El movimiento Puppet sigue pendiente.',
    'Pt': ' Movimento Puppet pendente.',
    'Ja': 'Puppetの移動は未実装です。',
    'Ko': ' Puppet 이동은 미구현입니다.',
}
lines = {
    'Eng': 'Puppet also supports Come here from its menu or the manager’s keyboard offsets. Its window moves toward the marker with the entire pet and marker constrained to the work area. Arrival is measured at the pet center and triggers the shared greeting after half a second. Dragging the pet, care, mode changes, hiding, resizing, screen-area changes or manual model commands cancel the call. A declared walk reaction is used while moving; models without one retain their native appearance. The movement timer runs only during a call. Native GL/focus acceptance remains pending.',
    'Zh': 'Puppet 也可從選單或管理頁鍵盤位移使用「過來這裡」。移動外層視窗，將整隻寵物與標記限制在工作區內；以寵物中心抵達判定，停留半秒後開始共用招呼。手動拖曳寵物、照顧、模式切換、隱藏、尺寸或工作區變更、手動模型指令會取消呼叫。有宣告 walk 反應的模型會播放對應動作，其餘維持原生外觀。移動計時器僅在呼叫期間運行。原生 GL／焦點驗收仍待完成。',
    'ZhCn': 'Puppet 也可从菜单或管理页键盘位移使用“过来这里”。移动外层窗口，将整只宠物和标记限制在工作区内；以宠物中心到达判定，停留半秒后开始共用招呼。手动拖动宠物、照护、模式切换、隐藏、尺寸或工作区变化、手动模型指令会取消呼叫。声明了 walk 反应的模型播放对应动作，其余保持原生外观。移动计时器仅在呼叫期间运行。原生 GL／焦点验收仍待完成。',
    'De': 'Puppet unterstützt Komm her über Menü oder Tastaturversatz im Manager. Das gesamte Tierfenster und die Markierung bleiben im Arbeitsbereich. Erreicht die Fenstermitte das Ziel für eine halbe Sekunde, startet der gemeinsame Gruß. Ziehen, Pflege, Moduswechsel, Ausblenden, Größen- oder Arbeitsbereichsänderungen und manuelle Modellbefehle brechen ab. Eine deklarierte walk-Reaktion wird verwendet; sonst bleibt die native Darstellung erhalten. Der Bewegungstimer läuft nur während des Rufs. Native GL-/Fokusprüfung steht aus.',
    'Fr': 'Puppet accepte aussi Viens ici depuis son menu ou les décalages clavier du gestionnaire. La fenêtre entière et le repère restent dans la zone de travail. Le centre atteint la cible pendant une demi-seconde avant la salutation commune. Déplacement manuel, soins, modes, masquage, changement de taille ou de zone et commandes du modèle annulent l’appel. Une réaction walk déclarée est utilisée, sinon l’apparence native reste intacte. Le minuteur ne tourne que pendant l’appel. Validation GL/focus native en attente.',
    'It': 'Puppet supporta Vieni qui dal menu o dagli scostamenti da tastiera del gestore. Finestra e segnaposto restano nell’area di lavoro. Il centro raggiunge la meta per mezzo secondo prima del saluto comune. Trascinamento, cura, modalità, nascondimento, modifiche a dimensioni o area e comandi manuali annullano il richiamo. Viene usata la reazione walk dichiarata, altrimenti resta l’aspetto nativo. Il timer funziona solo durante il richiamo. Verifica GL/focus nativa in sospeso.',
    'Ru': 'Puppet поддерживает Иди сюда через меню или смещения с клавиатуры в менеджере. Всё окно и метка ограничены рабочей областью. Когда центр достигает цели на полсекунды, начинается общее приветствие. Перетаскивание, уход, смена режима, скрытие, изменение размера или рабочей области и ручные команды модели отменяют вызов. Используется объявленная реакция walk, иначе сохраняется обычный вид. Таймер работает только во время вызова. Нативная проверка GL и фокуса ещё предстоит.',
    'Es': 'Puppet admite Ven aquí desde su menú o los desplazamientos de teclado del gestor. La ventana completa y el marcador quedan dentro del área de trabajo. Al llegar el centro y permanecer medio segundo, comienza el saludo compartido. Arrastrar, cuidar, cambiar modo, ocultar, redimensionar, cambiar el área o dar órdenes manuales cancela. Usa la reacción walk declarada; en su ausencia conserva el aspecto nativo. El temporizador solo funciona durante la llamada. Validación nativa GL/foco pendiente.',
    'Pt': 'Puppet também aceita Vem aqui pelo menu ou pelos deslocamentos de teclado do gerenciador. A janela inteira e o marcador ficam na área de trabalho. O centro chega ao destino por meio segundo antes do cumprimento compartilhado. Arrastar, cuidar, mudar modo, ocultar, redimensionar, alterar a área ou usar comandos manuais cancela. Usa a reação walk declarada; sem ela mantém o aspecto nativo. O temporizador roda apenas durante a chamada. Validação nativa GL/foco pendente.',
    'Ja': 'Puppetもメニューや管理画面のキーボード移動量から「ここに来て」を使えます。ウィンドウ全体とマーカーは作業領域内に制限され、中心が目的地に到着して半秒後に共通の挨拶を開始します。ドラッグ、世話、モード変更、非表示、サイズ・作業領域変更、モデルの手動操作で取消します。walk反応の指定があれば使用し、なければ元の外観を保ちます。移動タイマーは呼び出し中だけ動作します。ネイティブGL・フォーカス検証は未完了です。',
    'Ko': 'Puppet도 메뉴나 관리 화면의 키보드 이동량으로 이리 와를 사용할 수 있습니다. 창 전체와 표시는 작업 영역 안에 제한되며 중심이 목적지에 도착한 뒤 반 초 후 공통 인사를 시작합니다. 드래그, 돌봄, 모드 변경, 숨김, 크기·작업 영역 변경, 수동 모델 명령은 호출을 취소합니다. 선언된 walk 반응이 있으면 사용하고 없으면 원래 모습을 유지합니다. 이동 타이머는 호출 중에만 작동합니다. 네이티브 GL·포커스 검증은 미완료입니다.',
}
for filename, language in files.items():
    path = root / filename
    text = path.read_text(encoding='utf-8').replace(old[language], '')
    if lines[language] not in text:
        text = text.rstrip() + '\n\n' + lines[language] + '\n'
    path.write_text(text, encoding='utf-8', newline='\r\n')
previous = Path(__file__).with_name('update_call_docs.py')
text = previous.read_text(encoding='utf-8')
for sentence in old.values():
    text = text.replace(sentence, '')
previous.write_text(text, encoding='utf-8', newline='\r\n')
