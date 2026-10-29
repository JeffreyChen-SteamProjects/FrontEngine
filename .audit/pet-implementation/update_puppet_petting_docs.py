from pathlib import Path

root = Path(__file__).resolve().parents[2]
files = {'README.md': 'Eng', 'README/README_zh-TW.md': 'Zh', 'README/README_zh-CN.md': 'ZhCn',
         'README/README_de.md': 'De', 'README/README_fr.md': 'Fr', 'README/README_ru.md': 'Ru',
         'README/README_es.md': 'Es', 'README/README_pt-BR.md': 'Pt',
         'README/README_ja.md': 'Ja', 'README/README_ko.md': 'Ko'}
files.update({f'docs/source/docs/{lang}/pet.rst': lang for lang in ('Eng', 'Zh', 'ZhCn', 'De', 'Fr', 'It', 'Ru')})
lines = {
    'Eng': 'Puppet petting now waits for back-and-forth pointer strokes after choosing Pet gently. Leaving, Escape, hiding, changing mode or settling cancels unfinished petting. Dragging is suppressed while petting. Native gesture acceptance remains pending.',
    'Zh': 'Puppet 選擇撫摸後，需來回移動游標才開始互動；移開、Esc、隱藏、切換模式或安靜狀態會取消未完成撫摸。撫摸期間不拖曳視窗。原生手勢驗收仍待完成。',
    'ZhCn': 'Puppet 选择抚摸后，需来回移动光标才开始互动；移开、Esc、隐藏、切换模式或安静状态会取消未完成抚摸。抚摸期间不拖动窗口。原生手势验收仍待完成。',
    'De': 'Nach der Wahl von Streicheln startet Puppet die Interaktion erst bei Hin-und-her-Bewegungen des Zeigers. Verlassen, Esc, Ausblenden, Moduswechsel oder Ruhe brechen sie ab. Ziehen ist dabei gesperrt. Die native Gestenprüfung steht aus.',
    'Fr': 'Après le choix de caresser, Puppet attend des allers-retours du pointeur. Sortir, Échap, masquer, changer de mode ou immobiliser annule la caresse inachevée. Le déplacement de la fenêtre est bloqué pendant la caresse. Validation native des gestes en attente.',
    'It': 'Dopo la scelta di accarezzare, Puppet attende movimenti avanti e indietro del puntatore. Uscita, Esc, nascondimento, cambio modalità o quiete annullano la carezza incompleta. Il trascinamento è disabilitato durante la carezza. Verifica nativa dei gesti in sospeso.',
    'Ru': 'После выбора поглаживания Puppet ждёт движений указателя туда и обратно. Уход указателя, Esc, скрытие, смена режима или остановка отменяют незавершённое поглаживание. Перетаскивание в это время отключено. Нативная проверка жестов ещё предстоит.',
    'Es': 'Tras elegir acariciar, Puppet espera movimientos del puntero de ida y vuelta. Salir, Esc, ocultar, cambiar de modo o quedarse quieto cancela la caricia incompleta. No se arrastra la ventana al acariciar. Validación nativa de gestos pendiente.',
    'Pt': 'Após escolher acariciar, Puppet espera movimentos de ida e volta do ponteiro. Sair, Esc, ocultar, mudar de modo ou ficar quieto cancela o carinho incompleto. A janela não é arrastada durante o carinho. Validação nativa dos gestos pendente.',
    'Ja': 'Puppetは撫でる操作を選んだ後、ポインターを往復させると交流を開始します。範囲外への移動、Esc、非表示、モード変更、静止で未完了の交流を取り消します。撫でている間はドラッグしません。ネイティブのジェスチャー検証は未完了です。',
    'Ko': 'Puppet은 쓰다듬기를 선택한 뒤 포인터를 왕복해야 상호작용을 시작합니다. 영역 이탈, Esc, 숨김, 모드 변경 또는 정지 시 미완료 동작을 취소합니다. 쓰다듬는 동안 창을 드래그하지 않습니다. 네이티브 제스처 검증은 미완료입니다.',
}
for filename, lang in files.items():
    path = root / filename
    text = path.read_text(encoding='utf-8')
    if lines[lang] not in text:
        path.write_text(text.rstrip() + '\n\n' + lines[lang] + '\n', encoding='utf-8', newline='\r\n')
