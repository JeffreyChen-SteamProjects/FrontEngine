from pathlib import Path

root = Path(__file__).resolve().parents[2]
lines = {
'Eng': 'Peer greetings and tag require both pets to be visible, in Play mode, idle, socially enabled and not being carried or settled for typing. Unavailable pets are removed from targets and tag roles. Tag pauses below two eligible pets and resumes when they become available. Disabling speech bubbles only silences greeting text; it does not remove social rewards.',
'Zh': '互相打招呼與鬼抓人要求雙方都可見、處於玩耍模式且沒有正在互動、允許社交，也未被拖曳或因打字而安靜。不符合條件的寵物會退出追逐目標與角色。合適成員不足兩隻時暫停，恢復後再開始。關閉對話泡泡只隱藏招呼文字，不取消社交獎勵。',
'ZhCn': '互相打招呼与追逐游戏要求双方都可见、处于玩耍模式且没有正在互动、允许社交，也未被拖动或因打字而安静。不符合条件的宠物会退出追逐目标与角色。合适成员不足两只时暂停，恢复后再开始。关闭对话泡泡只隐藏招呼文字，不取消社交奖励。',
'De': 'Begrüßungen und Fangspiel erfordern zwei sichtbare Tiere im Spielmodus, ohne laufende Interaktion, mit erlaubtem Sozialverhalten und ohne Tragen oder Tipppause. Nicht verfügbare Tiere werden aus Zielen und Rollen entfernt. Unter zwei geeigneten Tieren pausiert das Spiel und wird später fortgesetzt. Deaktivierte Sprechblasen unterdrücken nur den Text, nicht die sozialen Belohnungen.',
'Fr': 'Salutations et poursuites exigent deux animaux visibles en mode jeu, sans interaction en cours, avec les échanges autorisés, sans transport ni pause de saisie. Les animaux indisponibles quittent les cibles et rôles. Le jeu se suspend sous deux participants admissibles et reprend à leur retour. Désactiver les bulles masque le texte, sans supprimer les récompenses sociales.',
'It': 'Saluti e inseguimenti richiedono entrambi gli animali visibili in modalità gioco, senza interazioni in corso, con socialità abilitata e senza trascinamento o pausa di digitazione. Gli animali non disponibili escono da bersagli e ruoli. Il gioco si ferma con meno di due partecipanti idonei e riprende al ritorno. Disattivare i fumetti nasconde solo il testo, non i premi sociali.',
'Ru': 'Приветствия и догонялки требуют, чтобы оба питомца были видимы, в режиме игры, без текущего взаимодействия, с разрешённым общением и без перетаскивания или паузы при наборе. Недоступные питомцы исключаются из целей и ролей. При числе участников меньше двух игра приостанавливается и возобновляется после их возвращения. Отключение облачков скрывает текст, но не отменяет награды за общение.',
'Es': 'Los saludos y las persecuciones requieren dos mascotas visibles en modo juego, sin interacción activa, con sociabilidad permitida y sin arrastre ni pausa al escribir. Las mascotas no disponibles dejan de ser objetivos o participantes. El juego pausa con menos de dos participantes aptos y se reanuda cuando vuelven. Desactivar los bocadillos solo oculta el texto, no las recompensas sociales.',
'Pt': 'Saudações e pega-pega exigem dois pets visíveis em modo de brincar, sem interação ativa, com socialização permitida e sem arrasto ou pausa ao digitar. Pets indisponíveis deixam de ser alvos ou participantes. O jogo pausa com menos de dois participantes aptos e retorna quando eles ficam disponíveis. Desativar balões só oculta o texto, não as recompensas sociais.',
'Ja': '挨拶や鬼ごっこには、双方が表示中で遊びモード、他の交流をしておらず、交流を許可し、ドラッグ中や入力時の休止中でもないことが必要です。参加できないペットは追跡対象と役割から外れます。参加可能なペットが2匹未満なら停止し、戻ると再開します。吹き出しを消しても交流報酬はなくなりません。',
'Ko': '인사와 술래잡기는 양쪽 펫이 보이는 상태로 놀이 모드에 있고, 다른 상호작용 중이 아니며, 교류를 허용하고, 드래그나 입력 중 정지 상태가 아니어야 합니다. 참여할 수 없는 펫은 추적 대상과 역할에서 제외됩니다. 참여 가능한 펫이 두 마리 미만이면 멈추고 복귀하면 재개됩니다. 말풍선을 꺼도 교류 보상은 유지됩니다.',
}
readmes = {'README.md':'Eng','README/README_zh-TW.md':'Zh','README/README_zh-CN.md':'ZhCn',
           'README/README_de.md':'De','README/README_fr.md':'Fr','README/README_ru.md':'Ru',
           'README/README_es.md':'Es','README/README_pt-BR.md':'Pt','README/README_ja.md':'Ja','README/README_ko.md':'Ko'}
targets = {root / path: lines[language] for path, language in readmes.items()}
targets.update({root / 'docs/source/docs' / language / 'pet.rst': lines[language]
                for language in ('Eng','Zh','ZhCn','De','Fr','It','Ru')})
for path, line in targets.items():
    text = path.read_text(encoding='utf-8')
    if line not in text:
        path.write_text(text.rstrip() + '\n\n' + line + '\n', encoding='utf-8', newline='\r\n')
