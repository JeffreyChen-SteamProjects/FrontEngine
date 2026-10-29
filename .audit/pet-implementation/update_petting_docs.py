from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
labels = {
'english': 'Move back and forth over the pet. Leave to stop.',
'traditional_chinese': '在寵物身上來回移動游標，移開即可結束。',
'simplified_chinese': '在宠物身上来回移动光标，移开即可结束。',
'germany': 'Zeiger über dem Tier hin und her bewegen. Zum Beenden wegbewegen.',
'france': 'Déplacez le pointeur sur l’animal en aller-retour. Éloignez-le pour arrêter.',
'italy': 'Muovi il puntatore avanti e indietro sull’animale. Allontanalo per terminare.',
'russian': 'Двигайте указатель по питомцу туда и обратно. Уведите его, чтобы закончить.',
}
for language, label in labels.items():
    path = root / 'frontengine/utils/multi_language' / (language + '.py')
    text = path.read_text(encoding='utf-8')
    if "'pet_petting_hint':" not in text:
        index = text.index("    'pet_photo_title':")
        text = text[:index] + "    'pet_petting_hint': " + repr(label) + ',\n' + text[index:]
        path.write_text(text, encoding='utf-8', newline='\n')
files = runpy.run_path(str(Path(__file__).with_name('update_focus_docs.py')))['files']
lines = {
'Eng': 'For sprite pets, choose Pet gently, then move the pointer back and forth over the pet. Three deliberate stroke segments start one petting reaction; jitter does not count. Dragging and social play pause during this mode. Leaving, hiding, changing mode or End interaction cancels unfinished petting. Rewards remain subject to completion and cooldown.',
'Zh': 'Sprite 寵物選「摸摸」後，在牠身上來回移動游標；三段明確行程才開始一次撫摸反應，細微抖動不算。期間暫停拖曳與社交；移開、隱藏、改變模式或選結束互動會取消未完成撫摸，獎勵仍須完成且遵守冷卻。',
'ZhCn': 'Sprite 宠物选“摸摸”后，在它身上来回移动光标；三段明确行程才开始一次抚摸反应，细微抖动不算。期间暂停拖动与社交；移开、隐藏、改变模式或选结束互动会取消未完成抚摸，奖励仍须完成且遵守冷却。',
'De': 'Bei Sprite-Tieren Sanft streicheln wählen und den Zeiger hin und her bewegen. Drei deutliche Streichelbewegungen starten eine Reaktion; Zittern zählt nicht. Ziehen und Sozialspiel pausieren. Wegbewegen, Verbergen, Moduswechsel oder Interaktion beenden bricht unfertiges Streicheln ab. Belohnungen erfordern Abschluss und Abklingzeit.',
'Fr': 'Pour les Sprite, choisissez Caresser puis déplacez le pointeur en aller-retour. Trois mouvements nets déclenchent une réaction ; les petits tremblements ne comptent pas. Déplacement et jeu social sont suspendus. Quitter, masquer, changer de mode ou terminer annule la caresse inachevée. Les récompenses exigent achèvement et délai de récupération.',
'It': 'Per gli Sprite scegli Accarezza e muovi il puntatore avanti e indietro. Tre movimenti netti avviano una reazione; piccoli tremori non contano. Trascinamento e gioco sociale si fermano. Uscire, nascondere, cambiare modalità o terminare annulla la carezza incompleta. I premi richiedono completamento e attesa.',
'Ru': 'Для Sprite выберите поглаживание и двигайте указатель туда и обратно. Три явных движения запускают реакцию; дрожание не считается. Перетаскивание и общение приостанавливаются. Уход указателя, скрытие, смена режима или завершение отменяет незаконченный жест. Награды требуют завершения и соблюдения задержки.',
'Es': 'En mascotas Sprite elige acariciar y mueve el puntero de un lado a otro. Tres movimientos claros inician una reacción; el temblor no cuenta. Arrastre y juego social se pausan. Salir, ocultar, cambiar de modo o terminar cancela la caricia incompleta. Los premios requieren finalización y respetan la espera.',
'Pt': 'Nos pets Sprite escolha acariciar e mova o ponteiro de um lado para o outro. Três movimentos claros iniciam uma reação; tremores não contam. Arrastar e brincar com outros pets ficam pausados. Sair, ocultar, mudar de modo ou terminar cancela a carícia incompleta. Prêmios exigem conclusão e intervalo.',
'Ja': 'Spriteでなでる操作を選び、ペット上でポインターを往復させます。明確な3区間の動きで反応し、小さな揺れは数えません。ドラッグと交流は停止します。離れる、非表示、モード変更、終了で未完了の操作を取り消します。報酬には完了とクールダウンが必要です。',
'Ko': 'Sprite에서 쓰다듬기를 선택하고 펫 위에서 포인터를 왕복하세요. 뚜렷한 세 구간 이동이 반응을 시작하며 작은 떨림은 제외합니다. 드래그와 사회적 놀이는 일시 중지됩니다. 벗어나기, 숨기기, 모드 변경 또는 종료는 미완료 행동을 취소합니다. 보상에는 완료와 대기 시간이 필요합니다.',
}
for filename, language in files.items():
    path = root / filename
    text = path.read_text(encoding='utf-8')
    if lines[language] not in text:
        path.write_text(text.rstrip() + '\n\n' + lines[language] + '\n', encoding='utf-8', newline='\r\n')
