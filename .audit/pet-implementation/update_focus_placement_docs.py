from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
files = runpy.run_path(str(Path(__file__).with_name('update_focus_docs.py')))['files']
lines = {
    'Eng': 'Focus mode arranges companions in the lower-right work area of their screen when space permits. Stopping restores their previous positions only if you have not moved them or changed their mode.',
    'Zh': '專注開始時，空間足夠的寵物會排列在所屬螢幕工作區右下角。停止時只恢復未被手動移動或改變模式的寵物原位置。',
    'ZhCn': '专注开始时，空间足够的宠物会排列在所属屏幕工作区右下角。停止时只恢复未被手动移动或改变模式的宠物原位置。',
    'De': 'Beim Fokusstart werden Tiere bei ausreichend Platz unten rechts im Arbeitsbereich ihres Bildschirms angeordnet. Beim Stop wird die alte Position nur ohne manuelle Bewegung oder Modusänderung wiederhergestellt.',
    'Fr': 'Au début de la concentration, les compagnons sont placés en bas à droite de leur écran si la place suffit. L’arrêt restaure leur position précédente seulement sans déplacement ni changement de mode manuel.',
    'It': 'All’avvio della concentrazione i compagni si dispongono in basso a destra nel proprio schermo se c’è spazio. Lo stop ripristina la posizione precedente solo senza spostamenti o cambi di modalità manuali.',
    'Ru': 'При запуске концентрации питомцы размещаются справа внизу рабочей области своего экрана, если хватает места. Остановка возвращает прежнюю позицию только без ручного перемещения или смены режима.',
    'Es': 'Al iniciar la concentración, las mascotas se sitúan abajo a la derecha de su pantalla si hay espacio. Al detenerla se restaura su posición anterior solo si no las moviste ni cambiaste su modo.',
    'Pt': 'Ao iniciar o foco, os pets ficam no canto inferior direito da área útil da própria tela se houver espaço. Parar restaura a posição anterior apenas sem movimento ou mudança de modo manual.',
    'Ja': '集中開始時、空きがあれば各画面の作業領域の右下にペットを並べます。停止時は、手動で移動やモード変更をしていないペットだけ元の位置に戻します。',
    'Ko': '집중 시작 시 공간이 있으면 각 화면 작업 영역의 오른쪽 아래에 펫을 배치합니다. 중지 시 수동 이동이나 모드 변경이 없었던 펫만 이전 위치로 돌아갑니다.',
}
for filename, language in files.items():
    path = root / filename
    content = path.read_text(encoding='utf-8')
    if lines[language] not in content:
        path.write_text(content.rstrip() + '\n\n' + lines[language] + '\n', encoding='utf-8', newline='\r\n')
