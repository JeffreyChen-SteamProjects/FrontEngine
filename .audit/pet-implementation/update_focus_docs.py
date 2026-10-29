from pathlib import Path

root = Path(__file__).resolve().parents[2]
lines = {
'Eng': 'Starting the pet focus timer puts currently visible, idle pets into Work mode; breaks use Rest mode. Stop restores previous modes unless you changed a mode yourself. Each completed focus round awards eligible visible companions 3 affection and 5 mood once; stopping early or hiding a pet gives no completion reward. Work/Rest suppress proactive chatter. The default timer uses monotonic elapsed time, not wall-clock changes.',
'Zh': '開始寵物專注計時會讓目前可見且沒有正在互動的寵物進入工作模式，休息階段改為休息模式。停止時恢復原模式，但不覆蓋手動更改的模式。每輪完成時，符合條件且可見的陪伴寵物只獲得一次 3 點好感與 5 點心情；提早停止或隱藏寵物不發完成獎勵。工作／休息模式不主動閒聊，預設計時採單調經過時間，不受系統時鐘調整影響。',
'ZhCn': '开始宠物专注计时会让当前可见且没有正在互动的宠物进入工作模式，休息阶段改为休息模式。停止时恢复原模式，但不覆盖手动更改的模式。每轮完成时，符合条件且可见的陪伴宠物只获得一次 3 点好感与 5 点心情；提前停止或隐藏宠物不发完成奖励。工作／休息模式不主动闲聊，默认计时采用单调经过时间，不受系统时钟调整影响。',
'De': 'Beim Start des Fokus-Timers wechseln sichtbare Tiere ohne laufende Interaktion in Arbeit, in Pausen in Ruhe. Stop stellt frühere Modi wieder her, sofern sie nicht manuell geändert wurden. Jede abgeschlossene Runde gibt geeigneten sichtbaren Begleitern einmal 3 Zuneigung und 5 Stimmung; vorzeitiger Stop oder Verbergen gibt keine Abschlussbelohnung. Arbeit/Ruhe unterdrückt spontane Gespräche. Der Timer nutzt monotone verstrichene Zeit statt Änderungen der Systemuhr.',
'Fr': 'Le minuteur de concentration place les animaux visibles sans interaction en mode Travail, puis Repos pendant les pauses. Arrêter rétablit les modes précédents sauf modification manuelle. Chaque tour terminé donne une seule fois 3 points d’affection et 5 d’humeur aux compagnons visibles admissibles ; arrêt anticipé ou masquage ne donne aucune récompense. Travail/Repos supprime les bavardages spontanés. Le minuteur utilise un temps écoulé monotone, indépendant de l’horloge système.',
'It': 'Il timer di concentrazione porta gli animali visibili senza interazioni in modalità Lavoro, poi Riposo nelle pause. Stop ripristina i modi precedenti salvo modifiche manuali. Ogni ciclo completo dà una sola volta 3 affetto e 5 umore ai compagni visibili idonei; interruzione anticipata o animali nascosti non ricevono il premio. Lavoro/Riposo blocca le chiacchiere spontanee. Il timer usa tempo trascorso monotono, indipendente dall’orologio di sistema.',
'Ru': 'Таймер концентрации переводит видимых питомцев без активного взаимодействия в режим работы, затем отдыха на перерывах. Остановка восстанавливает прежние режимы, кроме изменённых вручную. Завершённый раунд даёт подходящим видимым спутникам один раз 3 привязанности и 5 настроения; досрочная остановка и скрытие не дают награды. Работа/отдых отключает спонтанные реплики. Таймер использует монотонное время независимо от системных часов.',
'Es': 'El temporizador de concentración pone a las mascotas visibles sin interacción activa en Trabajo y después en Descanso durante las pausas. Detener restaura sus modos anteriores salvo cambios manuales. Cada ronda completa da una vez 3 de afecto y 5 de ánimo a los compañeros visibles aptos; detener antes o esconderlos no da premio. Trabajo/Descanso silencia charlas espontáneas. El reloj usa tiempo transcurrido monótono, no cambios de hora del sistema.',
'Pt': 'O timer de foco coloca pets visíveis sem interação ativa em Trabalho e depois Descanso nas pausas. Parar restaura os modos anteriores, exceto mudanças manuais. Cada rodada completa dá uma vez 3 de afeto e 5 de humor aos companheiros visíveis aptos; parar antes ou ocultar não dá prêmio. Trabalho/Descanso silencia conversas espontâneas. O timer usa tempo decorrido monotônico, independente do relógio do sistema.',
'Ja': '集中タイマーを開始すると、表示中で交流中でないペットが仕事モードになり、休憩では休息モードになります。停止時は元のモードに戻りますが、手動変更は上書きしません。各ラウンド完了時、条件を満たす表示中の仲間に好感度3と気分5を一度だけ付与します。途中停止や非表示では完了報酬はありません。仕事・休息では自発的なおしゃべりを抑え、計時にはシステム時計の変更に影響されない単調経過時間を使います。',
'Ko': '집중 타이머를 시작하면 표시 중이며 상호작용 중이 아닌 펫이 작업 모드로, 쉬는 시간에는 휴식 모드로 전환됩니다. 중지하면 원래 모드로 돌아가지만 수동 변경은 덮어쓰지 않습니다. 완료한 회차마다 조건에 맞는 표시 중인 펫에게 호감도 3과 기분 5를 한 번 줍니다. 조기 중지나 숨김에는 완료 보상이 없습니다. 작업/휴식은 자발적 대화를 억제하며 시스템 시계 변경에 영향받지 않는 단조 경과 시간을 사용합니다.',
}
files = {'README.md':'Eng','README/README_zh-TW.md':'Zh','README/README_zh-CN.md':'ZhCn','README/README_de.md':'De',
         'README/README_fr.md':'Fr','README/README_ru.md':'Ru','README/README_es.md':'Es','README/README_pt-BR.md':'Pt',
         'README/README_ja.md':'Ja','README/README_ko.md':'Ko'}
files.update({'docs/source/docs/' + lang + '/pet.rst':lang for lang in ('Eng','Zh','ZhCn','De','Fr','It','Ru')})
for file, lang in files.items():
    path = root / file
    text = path.read_text(encoding='utf-8')
    if lines[lang] not in text:
        path.write_text(text.rstrip() + '\n\n' + lines[lang] + '\n', encoding='utf-8', newline='\r\n')
