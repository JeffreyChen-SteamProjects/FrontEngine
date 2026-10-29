from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
labels = {
'english': 'The pet image is not ready. Show the pet and try again.',
'traditional_chinese': '寵物畫面尚未就緒，請顯示寵物後重試。',
'simplified_chinese': '宠物画面尚未就绪，请显示宠物后重试。',
'germany': 'Das Tierbild ist noch nicht bereit. Tier anzeigen und erneut versuchen.',
'france': 'L’image de l’animal n’est pas prête. Affichez l’animal et réessayez.',
'italy': 'L’immagine non è pronta. Mostra l’animale e riprova.',
'russian': 'Изображение питомца ещё не готово. Покажите питомца и повторите.',
}
for language, label in labels.items():
    path = root / 'frontengine/utils/multi_language' / (language + '.py')
    text = path.read_text(encoding='utf-8')
    if "'pet_photo_unavailable':" not in text:
        index = text.index("    'pet_photo_title':")
        text = text[:index] + "    'pet_photo_unavailable': " + repr(label) + ',\n' + text[index:]
        path.write_text(text, encoding='utf-8', newline='\n')
files = runpy.run_path(str(Path(__file__).with_name('update_focus_docs.py')))['files']
replacements = {
'Eng': ('Puppet photography is not yet supported.', 'Puppet pets also offer a frozen transparent photo through a compatible initialized Imervue renderer; no desktop pixels are captured. Native GL photo acceptance remains pending.'),
'Zh': ('Puppet 拍照尚未支援。', 'Puppet 也可透過已就緒且相容的 Imervue 渲染器拍攝透明定格照片，不讀取桌面像素。原生 GL 拍照驗收仍待完成。'),
'ZhCn': ('Puppet 拍照尚未支持。', 'Puppet 也可通过已就绪且兼容的 Imervue 渲染器拍摄透明定格照片，不读取桌面像素。原生 GL 拍照验收仍待完成。'),
'De': ('Puppet-Fotos werden noch nicht unterstützt.', 'Puppet-Fotos nutzen einen kompatiblen initialisierten Imervue-Renderer für transparente Standbilder ohne Desktop-Aufnahme. Die native GL-Abnahme steht noch aus.'),
'Fr': ('Les photos Puppet ne sont pas encore prises en charge.', 'Les photos Puppet utilisent un moteur Imervue compatible et initialisé pour une image transparente figée, sans capture du bureau. La validation GL native reste à faire.'),
'It': ('Le foto Puppet non sono ancora supportate.', 'Le foto Puppet usano un renderer Imervue compatibile e inizializzato per un’immagine trasparente fissa, senza catturare il desktop. La verifica GL nativa resta da eseguire.'),
'Ru': ('Фото Puppet пока не поддерживается.', 'Фото Puppet использует совместимый инициализированный рендерер Imervue для прозрачного стоп-кадра без захвата рабочего стола. Проверка нативного GL ещё предстоит.'),
'Es': ('Las fotos Puppet aún no están disponibles.', 'Las fotos Puppet usan un renderizador Imervue compatible e inicializado para una imagen transparente fija sin capturar el escritorio. La validación GL nativa sigue pendiente.'),
'Pt': ('Fotos Puppet ainda não são suportadas.', 'Fotos Puppet usam um renderizador Imervue compatível e inicializado para uma imagem transparente fixa sem capturar a área de trabalho. A validação GL nativa segue pendente.'),
'Ja': ('Puppetの撮影は未対応です。', 'Puppetは互換性のある初期化済みImervueレンダラーで透過静止画を撮影できます。デスクトップは取得しません。ネイティブGLの撮影検証は未完了です。'),
'Ko': ('Puppet 촬영은 아직 지원하지 않습니다.', 'Puppet은 호환되고 초기화된 Imervue 렌더러로 투명 정지 사진을 만들며 바탕 화면은 캡처하지 않습니다. 네이티브 GL 촬영 검증은 아직 미완료입니다.'),
}
for filename, language in files.items():
    path = root / filename
    text = path.read_text(encoding='utf-8')
    old, new = replacements[language]
    if old in text:
        path.write_text(text.replace(old, new), encoding='utf-8', newline='\r\n')
