from pathlib import Path

root = Path(__file__).resolve().parents[2]
lines = {
'Eng': 'If a pet save fails during close, the pet remains open with its current state and retry timer. Close all retains pets that could not close, and application exit waits for successful pet saves before teardown. Affection stops at the supported save limit so further rewards cannot make the profile unsaveable.',
'Zh': '關閉時若寵物存檔失敗，會保留寵物、目前狀態與重試計時器。「全部關閉」保留未能關閉的寵物；退出程式前會先確認寵物存檔成功。好感度到達存檔上限後不再增加，避免後續獎勵造成存檔失效。',
'ZhCn': '关闭时若宠物存档失败，会保留宠物、当前状态与重试计时器。“全部关闭”保留未能关闭的宠物；退出程序前会先确认宠物存档成功。好感度达到存档上限后不再增加，避免后续奖励造成存档失效。',
'De': 'Scheitert das Speichern beim Schließen, bleiben Tier, aktueller Zustand und Wiederholungs-Timer erhalten. Alle schließen behält Tiere, die nicht geschlossen werden konnten; vor dem Beenden müssen ihre Daten gespeichert sein. Zuneigung steigt nicht über die unterstützte Speichergrenze, damit weitere Belohnungen das Profil nicht ungültig machen.',
'Fr': 'Si l’enregistrement échoue à la fermeture, l’animal reste ouvert avec son état et le minuteur de nouvelle tentative. Tout fermer conserve les animaux non fermés ; quitter attend la réussite de leurs enregistrements avant de libérer les ressources. L’affection est plafonnée à la limite du format pour que les récompenses suivantes ne rendent pas le profil impossible à enregistrer.',
'It': 'Se il salvataggio fallisce durante la chiusura, l’animale resta aperto con lo stato attuale e il timer di ripetizione. Chiudi tutto conserva gli animali non chiusi; l’uscita attende il salvataggio prima di liberare le risorse. L’affetto si ferma al limite supportato, evitando profili non salvabili dopo ulteriori premi.',
'Ru': 'Если сохранение при закрытии не удалось, питомец остаётся открытым с текущим состоянием и таймером повтора. Закрыть всё сохраняет незакрытых питомцев; выход ждёт успешного сохранения перед освобождением ресурсов. Привязанность ограничена пределом формата, чтобы новые награды не мешали сохранению.',
'Es': 'Si falla el guardado al cerrar, la mascota sigue abierta con su estado y temporizador de reintento. Cerrar todo conserva las mascotas que no se pudieron cerrar; salir espera que se guarden antes de liberar recursos. El afecto se limita al máximo admitido para que futuras recompensas no impidan guardar.',
'Pt': 'Se o salvamento falhar ao fechar, o pet fica aberto com o estado atual e o temporizador de nova tentativa. Fechar tudo mantém os pets que não puderam fechar; sair aguarda o salvamento antes de liberar recursos. O afeto para no limite suportado para que novas recompensas não impeçam salvar.',
'Ja': '終了時に保存が失敗した場合、ペットは現在の状態と再試行タイマーを保って開いたままになります。すべて閉じるでも閉じられなかったペットは保持され、アプリ終了前に保存の成功を確認します。好感度は保存形式の上限で止まり、追加報酬で保存不能になることを防ぎます。',
'Ko': '닫을 때 저장에 실패하면 펫은 현재 상태와 재시도 타이머를 유지한 채 열려 있습니다. 모두 닫기도 닫지 못한 펫을 유지하며, 앱 종료 전에 저장 성공을 확인합니다. 호감도는 저장 형식의 상한에서 멈춰 추가 보상 때문에 저장할 수 없게 되는 문제를 막습니다.',
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
