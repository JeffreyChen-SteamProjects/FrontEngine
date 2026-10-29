from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
files = runpy.run_path(str(Path(__file__).with_name('update_focus_docs.py')))['files']
lines = {
'Eng': 'Puppet scripts may declare frontengine_actions to map companion states to existing model motions and expressions. Names are validated before startup; missing bindings do not guess animations. Completion releases reaction-owned effects while preserving manual choices. See docs/formats/puppet-companion-actions.md. Native visual acceptance remains pending.',
'Zh': 'Puppet 腳本可用 frontengine_actions 將共同互動狀態對應到模型已有動作與表情，啟動前驗證名稱；未設定時不猜動畫。完成後釋放互動持有的效果，保留手動選擇。格式見 docs/formats/puppet-companion-actions.md，原生視覺驗收仍待完成。',
'ZhCn': 'Puppet 脚本可用 frontengine_actions 将共同互动状态映射到模型已有动作与表情，启动前验证名称；未设置时不猜动画。完成后释放互动持有的效果，保留手动选择。格式见 docs/formats/puppet-companion-actions.md，原生视觉验收仍待完成。',
'De': 'Puppet-Skripte können mit frontengine_actions Zustände auf vorhandene Bewegungen und Ausdrücke abbilden. Namen werden vor dem Start geprüft; fehlende Bindungen raten keine Animation. Abschluss gibt reaktionseigene Effekte frei und erhält manuelle Auswahl. Format: docs/formats/puppet-companion-actions.md. Native Sichtprüfung steht aus.',
'Fr': 'Les scripts Puppet peuvent utiliser frontengine_actions pour relier les états aux mouvements et expressions existants. Les noms sont validés avant démarrage ; aucune animation n’est devinée. La fin libère les effets de réaction en gardant les choix manuels. Format : docs/formats/puppet-companion-actions.md. Validation visuelle native en attente.',
'It': 'Gli script Puppet possono usare frontengine_actions per associare stati a movimenti ed espressioni esistenti. I nomi sono verificati prima dell’avvio; nessuna animazione viene indovinata. Il completamento rilascia gli effetti della reazione e conserva le scelte manuali. Formato: docs/formats/puppet-companion-actions.md. Verifica visiva nativa in sospeso.',
'Ru': 'Скрипты Puppet могут задавать frontengine_actions для связи состояний с существующими движениями и выражениями. Имена проверяются до запуска; отсутствующие связи не угадываются. Завершение снимает эффекты реакции, сохраняя ручной выбор. Формат: docs/formats/puppet-companion-actions.md. Нативная визуальная проверка ещё предстоит.',
'Es': 'Los scripts Puppet pueden usar frontengine_actions para vincular estados a movimientos y expresiones existentes. Los nombres se validan antes de iniciar; no se adivinan animaciones. Al terminar se liberan efectos de reacción conservando elecciones manuales. Formato: docs/formats/puppet-companion-actions.md. Validación visual nativa pendiente.',
'Pt': 'Scripts Puppet podem usar frontengine_actions para ligar estados a movimentos e expressões existentes. Nomes são validados antes de iniciar; animações não são adivinhadas. Ao terminar, efeitos da reação são liberados e escolhas manuais mantidas. Formato: docs/formats/puppet-companion-actions.md. Validação visual nativa pendente.',
'Ja': 'Puppetスクリプトのfrontengine_actionsで交流状態を既存の動作や表情へ対応付けできます。起動前に名前を検証し、未指定の動作は推測しません。完了時は反応用の効果だけ解除し、手動選択を保ちます。形式はdocs/formats/puppet-companion-actions.mdを参照。ネイティブの視覚検証は未完了です。',
'Ko': 'Puppet 스크립트의 frontengine_actions로 상호작용 상태를 기존 동작과 표정에 연결할 수 있습니다. 시작 전에 이름을 검증하며 미지정 동작은 추측하지 않습니다. 완료 시 반응 효과만 해제하고 수동 선택은 유지합니다. 형식은 docs/formats/puppet-companion-actions.md 참고. 네이티브 시각 검증은 미완료입니다.',
}
for filename, language in files.items():
    path = root / filename
    text = path.read_text(encoding='utf-8')
    if lines[language] not in text:
        path.write_text(text.rstrip() + '\n\n' + lines[language] + '\n', encoding='utf-8', newline='\r\n')
