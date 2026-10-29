from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
translations = {
    'english': ('Character part', 'Part style'),
    'traditional_chinese': ('角色部件', '部件樣式'),
    'simplified_chinese': ('角色部件', '部件样式'),
    'germany': ('Charakterteil', 'Teilstil'),
    'france': ('Élément du personnage', 'Style de l’élément'),
    'italy': ('Parte del personaggio', 'Stile della parte'),
    'russian': ('Часть персонажа', 'Вариант части'),
}
for language, labels in translations.items():
    path = root / 'frontengine/utils/multi_language' / (language + '.py')
    content = path.read_text(encoding='utf-8')
    if "'pet_wardrobe_part':" not in content:
        index = content.index("    'pet_wardrobe_region':")
        content = content[:index] + ''.join('    ' + repr(key) + ': ' + repr(label) + ',\n'
            for key, label in zip(('pet_wardrobe_part', 'pet_wardrobe_part_choice'), labels)) + content[index:]
        path.write_text(content, encoding='utf-8', newline='\n')

files = runpy.run_path(str(Path(__file__).with_name('update_focus_docs.py')))['files']
lines = {
    'Eng': 'Layered characters can declare selectable face/body parts. Wardrobe previews part choices per pet; Apply persists them and saved outfits retain the character and parts. Every declared choice must cover every animation frame. Production artwork for the six characters remains unfinished.',
    'Zh': '分層角色可宣告五官與身體部件選項；衣櫃按個體預覽，套用後保存，搭配收藏同時保留角色及部件。每個選項必須涵蓋所有動畫幀。六角色正式部件美術仍未完成。',
    'ZhCn': '分层角色可声明五官与身体部件选项；衣柜按个体预览，应用后保存，搭配收藏同时保留角色及部件。每个选项必须涵盖所有动画帧。六角色正式部件美术仍未完成。',
    'De': 'Mehrschichtige Charaktere können Gesichts- und Körpervarianten anbieten. Die Garderobe zeigt eine Vorschau pro Tier; Anwenden speichert sie, Outfits behalten Charakter und Teile. Jede Variante muss alle Animationsbilder abdecken. Die fertigen Grafiken der sechs Charaktere fehlen noch.',
    'Fr': 'Les personnages en calques peuvent proposer des variantes de visage et de corps. La garde-robe les prévisualise par animal ; Appliquer les enregistre, et les tenues conservent personnage et éléments. Chaque variante doit couvrir toutes les images d’animation. Les graphismes définitifs des six personnages restent à produire.',
    'It': 'I personaggi a livelli possono offrire varianti del viso e del corpo. Il guardaroba le mostra per animale; Applica le salva e gli abiti conservano personaggio e parti. Ogni variante deve coprire tutti i fotogrammi. La grafica definitiva dei sei personaggi resta da realizzare.',
    'Ru': 'Послойные персонажи могут предлагать варианты лица и тела. Гардероб показывает их для каждого питомца; применение сохраняет выбор, а комплекты сохраняют персонажа и части. Каждый вариант должен покрывать все кадры. Финальная графика шести персонажей ещё не готова.',
    'Es': 'Los personajes por capas pueden ofrecer variantes de cara y cuerpo. El vestuario permite previsualizarlas por mascota; Aplicar guarda la selección y los conjuntos conservan personaje y partes. Cada variante debe cubrir todos los fotogramas. El arte definitivo de los seis personajes sigue pendiente.',
    'Pt': 'Personagens em camadas podem oferecer variantes de rosto e corpo. O guarda-roupa mostra a prévia por pet; Aplicar salva a seleção e os conjuntos guardam personagem e partes. Cada variante deve cobrir todos os quadros. A arte final dos seis personagens ainda está pendente.',
    'Ja': 'レイヤー式キャラクターは顔や体のパーツ選択肢を定義できます。衣装画面で個体ごとに試し、適用して保存します。保存コーデにはキャラクターとパーツも含まれます。各選択肢には全アニメーションフレームが必要です。6キャラクターの正式な素材は未完成です。',
    'Ko': '레이어 캐릭터는 얼굴과 몸 부품 선택지를 정의할 수 있습니다. 옷장에서 개체별로 미리 보고 적용하여 저장하며 저장한 조합에는 캐릭터와 부품도 포함됩니다. 모든 선택지는 전체 애니메이션 프레임을 제공해야 합니다. 여섯 캐릭터의 최종 아트는 아직 미완성입니다.',
}
for filename, language in files.items():
    path = root / filename
    content = path.read_text(encoding='utf-8')
    if lines[language] not in content:
        path.write_text(content.rstrip() + '\n\n' + lines[language] + '\n', encoding='utf-8', newline='\r\n')
