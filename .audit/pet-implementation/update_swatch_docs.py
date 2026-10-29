import json
from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
labels = {'english': 'Style colors', 'traditional_chinese': '風格色票',
          'simplified_chinese': '风格色板', 'germany': 'Stilfarben',
          'france': 'Couleurs du style', 'italy': 'Colori dello stile', 'russian': 'Цвета стиля'}
for language, label in labels.items():
    path = root / 'frontengine/utils/multi_language' / (language + '.py')
    text = path.read_text(encoding='utf-8')
    key = 'pet_wardrobe_swatches'
    if repr(key) not in text:
        index = text.rfind('}')
        text = text[:index] + f'    {key!r}: ' + json.dumps(label, ensure_ascii=False) + ',\n' + text[index:]
        path.write_text(text, encoding='utf-8', newline='\n')

files = runpy.run_path(str(Path(__file__).with_name('update_puppet_petting_docs.py')))['files']
lines = {
    'Eng': 'Wardrobe style colors offer six quick swatches for the selected declared color region. Preview first, then Apply; Cancel preserves the saved appearance. Free color selection and restoring the region default remain available.',
    'Zh': '衣櫃提供六個風格色票，可快速調整選取的素材配色部位。先預覽再套用；取消保留已存外觀。仍可自由選色及恢復部位原色。',
    'ZhCn': '衣柜提供六个风格色板，可快速调整选中的素材配色部位。先预览再应用；取消保留已存外观。仍可自由选色及恢复部位原色。',
    'De': 'Die Garderobe bietet sechs Stilfarben für den gewählten Farbbereich des Assets. Erst Vorschau, dann Anwenden; Abbrechen erhält das gespeicherte Aussehen. Freie Farbwahl und Zurücksetzen bleiben verfügbar.',
    'Fr': 'La garde-robe propose six couleurs rapides pour la zone déclarée sélectionnée. Prévisualisez puis appliquez ; Annuler conserve l’apparence enregistrée. Le choix libre et la couleur par défaut restent disponibles.',
    'It': 'Il guardaroba offre sei colori rapidi per la zona dichiarata selezionata. Anteprima e poi Applica; Annulla conserva l’aspetto salvato. Restano disponibili scelta libera e ripristino del colore.',
    'Ru': 'Гардероб предлагает шесть цветов для выбранной области ресурса. Сначала предпросмотр, затем применение; отмена сохраняет записанный внешний вид. Свободный выбор и возврат исходного цвета доступны.',
    'Es': 'El vestuario ofrece seis colores rápidos para la zona declarada seleccionada. Previsualiza y aplica; Cancelar conserva la apariencia guardada. También permite elegir libremente y restaurar el color original.',
    'Pt': 'O guarda-roupa oferece seis cores rápidas para a região declarada selecionada. Pré-visualize e aplique; Cancelar mantém a aparência salva. A escolha livre e a restauração da cor original continuam disponíveis.',
    'Ja': '衣装画面に、選択した素材の色領域へ使える6色の色見本を追加しました。プレビュー後に適用し、キャンセル時は保存済みの外観を保ちます。自由な色選択と初期色への復元も可能です。',
    'Ko': '옷장에서 선택한 소재 색상 영역에 사용할 여섯 가지 색상 견본을 제공합니다. 미리 본 뒤 적용하며, 취소하면 저장된 외형을 유지합니다. 자유로운 색 선택과 원래 색 복원도 가능합니다.',
}
for filename, lang in files.items():
    path = root / filename
    text = path.read_text(encoding='utf-8')
    if lines[lang] not in text:
        path.write_text(text.rstrip() + '\n\n' + lines[lang] + '\n', encoding='utf-8', newline='\r\n')
