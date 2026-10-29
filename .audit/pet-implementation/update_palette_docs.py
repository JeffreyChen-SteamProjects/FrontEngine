from pathlib import Path
import json

root = Path(__file__).resolve().parents[2]
labels = {
    'english': ['Color region', 'Choose color', 'Restore region color'],
    'traditional_chinese': ['配色部位', '選擇顏色', '恢復部位原色'],
    'simplified_chinese': ['配色部位', '选择颜色', '恢复部位原色'],
    'germany': ['Farbbereich', 'Farbe wählen', 'Bereichsfarbe zurücksetzen'],
    'france': ['Zone de couleur', 'Choisir la couleur', 'Rétablir la couleur de la zone'],
    'italy': ['Zona colore', 'Scegli colore', 'Ripristina colore della zona'],
    'russian': ['Цветовая область', 'Выбрать цвет', 'Восстановить цвет области'],
}
for language, values in labels.items():
    path = root / 'frontengine/utils/multi_language' / (language + '.py')
    text = path.read_text(encoding='utf-8')
    for suffix, value in zip(('region', 'color', 'color_reset'), values):
        key = 'pet_wardrobe_' + suffix
        if repr(key) not in text:
            index = text.rfind('}')
            text = text[:index] + '    ' + repr(key) + ': ' + json.dumps(value, ensure_ascii=False) + ',\n' + text[index:]
    path.write_text(text, encoding='utf-8', newline='\n')

paragraphs = {
    'Eng': 'Wardrobe color controls appear for regions declared by the selected character or clothing asset. Choose a region and color, or restore its authored color. Only designated mask layers are tinted; outlines and unmarked details remain unchanged. Colors are previewed before Apply and saved per identity and outfit, including profile export/import. Assets without declared regions have no color controls enabled.',
    'Zh': '衣櫃會列出角色或服裝素材宣告的配色部位。選取部位後可改色或恢復素材原色；只改指定遮罩圖層，輪廓與未標記細節保持不變。配色先預覽，按套用才保存，並隨個體、收藏搭配及存檔匯出／匯入保留。未宣告部位的素材不開放配色控制。',
    'ZhCn': '衣柜会列出角色或服装素材声明的配色部位。选择部位后可改色或恢复素材原色；只改指定遮罩图层，轮廓与未标记细节保持不变。配色先预览，点击应用才保存，并随个体、收藏搭配及存档导出／导入保留。未声明部位的素材不开放配色控制。',
    'De': 'Die Garderobe zeigt Farbbereiche an, die Figur oder Kleidung deklarieren. Wähle einen Bereich und eine Farbe oder stelle die Originalfarbe wieder her. Nur markierte Maskenebenen werden eingefärbt; Konturen und andere Details bleiben erhalten. Farben werden vor dem Anwenden angezeigt und je Identität und Outfit gespeichert, auch beim Export/Import. Ohne deklarierte Bereiche bleiben Farbregler deaktiviert.',
    'Fr': 'La garde-robe propose les zones de couleur déclarées par le personnage ou le vêtement. Choisissez une zone et une couleur, ou rétablissez la couleur originale. Seuls les calques de masque désignés sont colorés ; les contours et autres détails sont conservés. Les couleurs sont prévisualisées avant application et sauvegardées par identité et tenue, y compris à l’export/import. Sans zones déclarées, ces commandes restent désactivées.',
    'It': 'Il guardaroba mostra le zone colore dichiarate dal personaggio o dall’abito. Scegli zona e colore oppure ripristina l’originale. Si colorano solo i livelli maschera designati; contorni e altri dettagli restano invariati. I colori si vedono prima di Applica e vengono salvati per identità e completo, anche nell’esportazione/importazione. Senza zone dichiarate i controlli sono disattivati.',
    'Ru': 'Гардероб показывает цветовые области, объявленные персонажем или одеждой. Выберите область и цвет либо восстановите исходный цвет. Окрашиваются только указанные слои-маски; контуры и прочие детали сохраняются. Цвета видны до применения и сохраняются для питомца и наряда, включая экспорт/импорт. Без объявленных областей управление цветом отключено.',
    'Es': 'El armario muestra las zonas de color declaradas por el personaje o la ropa. Elige zona y color o restaura el original. Solo se tiñen las capas de máscara designadas; los contornos y otros detalles se conservan. Los colores se previsualizan antes de aplicar y se guardan por identidad y conjunto, también al exportar/importar. Sin zonas declaradas, los controles quedan desactivados.',
    'Pt': 'O guarda-roupa mostra as regiões de cor declaradas pelo personagem ou roupa. Escolha região e cor ou restaure a original. Somente as camadas de máscara indicadas são tingidas; contornos e outros detalhes são preservados. As cores são exibidas antes de aplicar e salvas por identidade e conjunto, inclusive na exportação/importação. Sem regiões declaradas, os controles ficam desativados.',
    'Ja': 'ワードローブにはキャラクターや衣装が宣言した配色部位が表示されます。部位と色を選ぶか、元の色に戻せます。指定されたマスクレイヤーだけを着色し、輪郭と未指定の細部は維持します。適用前にプレビューでき、個体とコーディネートに保存され、書き出し／読み込みにも含まれます。配色部位のない素材では色の操作は無効です。',
    'Ko': '옷장에는 캐릭터나 의상이 선언한 색상 영역이 표시됩니다. 영역과 색을 선택하거나 원래 색으로 복원합니다. 지정된 마스크 레이어만 바뀌며 윤곽과 나머지 세부 묘사는 유지됩니다. 적용 전 미리 볼 수 있고 개체와 의상 조합별로 저장되며 내보내기/가져오기에도 포함됩니다. 영역을 선언하지 않은 소재에서는 색상 조작이 비활성화됩니다.',
}
readmes = {'README.md':'Eng', 'README/README_zh-TW.md':'Zh', 'README/README_zh-CN.md':'ZhCn',
           'README/README_de.md':'De', 'README/README_fr.md':'Fr', 'README/README_ru.md':'Ru',
           'README/README_es.md':'Es', 'README/README_pt-BR.md':'Pt', 'README/README_ja.md':'Ja', 'README/README_ko.md':'Ko'}
targets = {root / file: paragraphs[lang] for file, lang in readmes.items()}
targets.update({root / 'docs/source/docs' / lang / 'pet.rst': paragraphs[lang] for lang in ('Eng', 'Zh', 'ZhCn', 'De', 'Fr', 'It', 'Ru')})
for path, paragraph in targets.items():
    text = path.read_text(encoding='utf-8')
    if paragraph not in text:
        path.write_text(text.rstrip() + '\n\n' + paragraph + '\n', encoding='utf-8', newline='\r\n')
