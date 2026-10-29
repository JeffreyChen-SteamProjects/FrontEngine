from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
files = runpy.run_path(str(Path(__file__).with_name('update_focus_docs.py')))['files']
lines = {
'Eng': 'Floor pets leave window ledges to fetch a ball. Window perching pauses during the game and resumes afterward; the return point is on the floor near the original horizontal position.',
'Zh': '地板模式寵物會離開窗沿下到地板追球；玩球期間暫停視窗停靠，結束後恢復。帶回位置在原起點水平位置附近的地板。',
'ZhCn': '地板模式宠物会离开窗沿下到地板追球；玩球期间暂停窗口停靠，结束后恢复。带回位置在原起点水平位置附近的地板。',
'De': 'Bodentiere verlassen Fensterkanten zum Ballholen. Fensterplätze pausieren während des Spiels und werden danach wieder genutzt; die Rückkehr erfolgt am Boden nahe der ursprünglichen horizontalen Position.',
'Fr': 'Les animaux au sol quittent les rebords pour chercher la balle. Les perchoirs de fenêtre sont suspendus pendant le jeu puis réactivés ; le retour se fait au sol près de la position horizontale initiale.',
'It': 'Gli animali a terra lasciano i bordi delle finestre per recuperare la palla. Le soste sulle finestre si sospendono durante il gioco e riprendono dopo; il ritorno avviene a terra vicino alla posizione orizzontale iniziale.',
'Ru': 'Наземные питомцы покидают края окон ради мяча. Посадка на окна приостанавливается на время игры и возобновляется после неё; возврат происходит на полу рядом с исходной горизонтальной позицией.',
'Es': 'Las mascotas de suelo bajan de las ventanas para buscar la pelota. Posarse en ventanas se pausa durante el juego y se reanuda después; regresan al suelo cerca de la posición horizontal inicial.',
'Pt': 'Pets de chão descem das janelas para buscar a bola. Pousar em janelas fica pausado durante o jogo e volta depois; o retorno é no chão perto da posição horizontal inicial.',
'Ja': '床モードのペットは窓辺から降りてボールを追います。遊んでいる間は窓への着地を停止し、終了後に再開します。持ち帰る場所は開始時の横位置に近い床です。',
'Ko': '바닥 모드 펫은 창가에서 내려와 공을 쫓습니다. 놀이 중에는 창가 앉기를 중지하고 끝나면 재개합니다. 돌아오는 곳은 시작한 가로 위치 근처의 바닥입니다.',
}
for filename, language in files.items():
    path = root / filename
    text = path.read_text(encoding='utf-8')
    if lines[language] not in text:
        path.write_text(text.rstrip() + '\n\n' + lines[language] + '\n', encoding='utf-8', newline='\r\n')
