from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
files = runpy.run_path(str(Path(__file__).with_name('update_focus_docs.py')))['files']
lines = {
'Eng': 'Eligible focus completion briefly requests the celebrate animation, then returns to Rest. Applying a changed wardrobe briefly requests outfit_show. These two-second active-time reactions add no rewards and are not saved; manual actions or mode changes interrupt them. Assets without those animations use the existing idle fallback. Finished reaction artwork and native Puppet animation mapping remain pending.',
'Zh': '符合條件的專注完成會短暫播放 celebrate，再回休息；套用變更的衣櫃會短暫播放 outfit_show。反應持續兩秒活躍時間，不另給獎勵、不寫入存檔，手動互動或換模式可中斷。素材缺少對應動畫時沿用 idle 回退；正式反應美術與 Puppet 動畫對應仍待完成。',
'ZhCn': '符合条件的专注完成会短暂播放 celebrate，再回休息；应用更改的衣柜会短暂播放 outfit_show。反应持续两秒活跃时间，不另给奖励、不写入存档，手动互动或换模式可中断。素材缺少对应动画时沿用 idle 回退；正式反应美术与 Puppet 动画映射仍待完成。',
'De': 'Ein geeigneter Fokusabschluss fordert kurz celebrate an, danach folgt Ruhe. Geänderte Garderoben fordern outfit_show an. Die Reaktionen dauern zwei aktive Sekunden, geben keine Zusatzbelohnung und werden nicht gespeichert; manuelle Aktionen oder Modi unterbrechen sie. Fehlende Animationen nutzen idle. Fertige Grafiken und Puppet-Zuordnung stehen aus.',
'Fr': 'Une concentration terminée admissible déclenche brièvement celebrate puis Repos. Une tenue modifiée déclenche outfit_show. Ces réactions durent deux secondes actives, sans récompense supplémentaire ni sauvegarde ; actions ou modes manuels les interrompent. Les animations absentes utilisent idle. Les graphismes finaux et la correspondance Puppet restent à faire.',
'It': 'Il completamento valido della concentrazione richiede celebrate e poi Riposo. Un cambio di guardaroba richiede outfit_show. Le reazioni durano due secondi attivi, senza premi aggiuntivi né salvataggio; azioni o modalità manuali le interrompono. Animazioni mancanti usano idle. Grafica finale e associazioni Puppet restano da fare.',
'Ru': 'Допустимое завершение концентрации кратко включает celebrate, затем отдых. Изменение гардероба включает outfit_show. Реакции длятся две активные секунды, не дают дополнительных наград и не сохраняются; ручные действия и режимы прерывают их. При отсутствии анимации используется idle. Финальная графика и соответствия Puppet ещё не готовы.',
'Es': 'Completar una sesión válida solicita celebrate y luego Descanso. Aplicar un vestuario cambiado solicita outfit_show. Duran dos segundos activos, sin premios extra ni guardado; acciones o modos manuales interrumpen. Animaciones ausentes usan idle. El arte final y la adaptación Puppet siguen pendientes.',
'Pt': 'Concluir uma sessão válida solicita celebrate e depois Descanso. Aplicar um figurino alterado solicita outfit_show. Duram dois segundos ativos, sem prêmios extras nem salvamento; ações ou modos manuais interrompem. Animações ausentes usam idle. Arte final e adaptação Puppet seguem pendentes.',
'Ja': '対象の集中完了時にcelebrateを短く再生して休息へ戻り、衣装変更の適用時はoutfit_showを要求します。反応は活動時間2秒で、追加報酬や保存はなく、手動操作やモード変更で中断します。素材にアニメーションがなければidleを使います。正式素材とPuppet対応は未完成です。',
'Ko': '조건에 맞는 집중 완료 시 celebrate를 잠시 재생하고 휴식으로 돌아가며 옷장 변경 적용 시 outfit_show를 요청합니다. 활동 시간 2초 동안 추가 보상이나 저장 없이 표시하고 수동 행동 또는 모드 변경으로 중단합니다. 없는 애니메이션은 idle을 사용합니다. 최종 아트와 Puppet 연결은 아직 미완성입니다.',
}
for filename, language in files.items():
    path = root / filename
    text = path.read_text(encoding='utf-8')
    if lines[language] not in text:
        path.write_text(text.rstrip() + '\n\n' + lines[language] + '\n', encoding='utf-8', newline='\r\n')
