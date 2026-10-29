from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
files = runpy.run_path(str(Path(__file__).with_name('update_puppet_petting_docs.py')))['files']
lines = {
    'Eng': 'Changing the interface language while the wardrobe is open updates its None, Missing and Reset defaults choices without discarding pending colors, parts, outfit names or the preview position. Asset-provided names stay as authored.',
    'Zh': '衣櫃開啟時切換介面語言，會更新「無」、「缺少素材」與「重設預設」選項，保留未套用的配色、部件、穿搭名稱及預覽進度。素材作者提供的名稱維持原文。',
    'ZhCn': '衣柜打开时切换界面语言，会更新“无”、“缺少素材”和“重设默认”选项，保留未应用的配色、部件、穿搭名称和预览进度。素材作者提供的名称保持原文。',
    'De': 'Beim Sprachwechsel in der geöffneten Garderobe werden die Optionen für keine Auswahl, fehlende Ressourcen und Standardwerte aktualisiert. Entwürfe für Farben, Teile und Outfitnamen sowie die Vorschauposition bleiben erhalten. Ressourcennamen bleiben im Original.',
    'Fr': 'Changer la langue avec la garde-robe ouverte actualise les choix Aucun, Manquant et Valeurs par défaut. Les couleurs, pièces, noms de tenues non appliqués et la position de l’aperçu sont conservés. Les noms fournis par les auteurs restent inchangés.',
    'It': 'Cambiare lingua con il guardaroba aperto aggiorna le opzioni Nessuno, Mancante e Ripristina predefiniti. Colori, parti, nomi degli abiti non applicati e posizione dell’anteprima restano invariati. I nomi delle risorse rimangono quelli originali.',
    'Ru': 'Смена языка при открытом гардеробе обновляет пункты отсутствия выбора, недостающих ресурсов и сброса настроек. Несохранённые цвета, детали, названия нарядов и позиция предпросмотра сохраняются. Авторские названия ресурсов не переводятся.',
    'Es': 'Cambiar el idioma con el vestuario abierto actualiza las opciones Ninguno, Falta y Restablecer valores. Conserva colores, piezas, nombres de conjuntos pendientes y la posición de la vista previa. Los nombres de recursos mantienen el texto del autor.',
    'Pt': 'Mudar o idioma com o guarda-roupa aberto atualiza as opções Nenhum, Ausente e Restaurar padrões. Preserva cores, peças, nomes de conjuntos pendentes e a posição da prévia. Os nomes dos recursos mantêm o texto do autor.',
    'Ja': '衣装画面を開いたまま言語を切り替えると、なし・素材不足・初期設定の選択肢が更新されます。未適用の色、パーツ、衣装名、プレビュー位置は保持されます。素材名は作者の原文のままです。',
    'Ko': '옷장을 연 상태에서 언어를 바꾸면 없음, 누락된 소재, 기본값 복원 항목이 갱신됩니다. 적용 전 색상, 부품, 의상 이름과 미리보기 위치는 유지됩니다. 소재 이름은 제작자의 원문을 유지합니다.',
}
for filename, language in files.items():
    path = root / filename
    text = path.read_text(encoding='utf-8')
    if lines[language] not in text:
        path.write_text(text.rstrip() + '\n\n' + lines[language] + '\n', encoding='utf-8', newline='\r\n')
