import json
from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
labels = {
    'english': ['No preference', 'Favorite treat', 'Disliked treat', 'Choose different treats for favorite and disliked.'],
    'traditional_chinese': ['無偏好', '喜歡的點心', '不喜歡的點心', '喜歡與不喜歡的點心請選不同種類。'],
    'simplified_chinese': ['无偏好', '喜欢的点心', '不喜欢的点心', '喜欢与不喜欢的点心请选择不同种类。'],
    'germany': ['Keine Vorliebe', 'Lieblingsleckerbissen', 'Unbeliebter Leckerbissen', 'Wählen Sie unterschiedliche beliebte und unbeliebte Leckerbissen.'],
    'france': ['Aucune préférence', 'Friandise préférée', 'Friandise moins aimée', 'Choisissez deux friandises différentes.'],
    'italy': ['Nessuna preferenza', 'Spuntino preferito', 'Spuntino sgradito', 'Scegli spuntini diversi come preferito e sgradito.'],
    'russian': ['Без предпочтений', 'Любимое угощение', 'Нелюбимое угощение', 'Выберите разные любимое и нелюбимое угощения.'],
}
keys = ['pet_taste_none', 'pet_taste_favorite', 'pet_taste_disliked', 'pet_taste_conflict']
for language, values in labels.items():
    path = root / 'frontengine/utils/multi_language' / (language + '.py')
    text = path.read_text(encoding='utf-8')
    for key, value in zip(keys, values):
        if repr(key) not in text:
            index = text.rfind('}')
            text = text[:index] + f'    {key!r}: ' + json.dumps(value, ensure_ascii=False) + ',\n' + text[index:]
    path.write_text(text, encoding='utf-8', newline='\n')

files = runpy.run_path(str(Path(__file__).with_name('update_puppet_petting_docs.py')))['files']
lines = {
    'Eng': 'Each pet can save a favorite and a different disliked treat in Customize pet. These affect mood only after feeding completes; fullness, affection and cooldown are unchanged. Mid-meal edits affect the next meal. Old profiles remain neutral. Optional food_like and food_dislike artwork or Puppet bindings provide short reactions; production artwork is pending.',
    'Zh': '每隻寵物可在自訂中保存喜歡與不喜歡的不同點心。只在餵食完成後調整心情，飽足、好感與冷卻不變；進食中改設定從下一餐生效。舊存檔預設無偏好。素材或 Puppet 可提供 food_like、food_dislike 短反應，正式動畫仍待製作。',
    'ZhCn': '每只宠物可在自定义中保存喜欢与不喜欢的不同点心。只在喂食完成后调整心情，饱足、好感与冷却不变；进食中改设置从下一餐生效。旧存档默认无偏好。素材或 Puppet 可提供 food_like、food_dislike 短反应，正式动画仍待制作。',
    'De': 'Jedes Tier kann einen beliebten und einen anderen unbeliebten Leckerbissen speichern. Nur die Stimmung nach dem Fressen ändert sich; Sättigung, Zuneigung und Wartezeit bleiben gleich. Änderungen gelten ab der nächsten Mahlzeit. Alte Profile sind neutral. food_like und food_dislike sind optionale Reaktionen; fertige Animationen stehen aus.',
    'Fr': 'Chaque animal peut enregistrer deux friandises différentes, préférée et moins aimée. Seule l’humeur après le repas change ; satiété, affection et délai restent identiques. Les modifications en cours de repas prennent effet au suivant. Les anciens profils sont neutres. food_like et food_dislike sont optionnels ; animations finales en attente.',
    'It': 'Ogni animale può salvare uno spuntino preferito e uno diverso sgradito. Cambia solo l’umore a pasto concluso; sazietà, affetto e attesa restano invariati. Modifiche durante il pasto valgono dal successivo. I vecchi profili sono neutrali. food_like e food_dislike sono opzionali; animazioni finali in sospeso.',
    'Ru': 'Для каждого питомца можно сохранить разные любимое и нелюбимое угощения. Меняется только настроение после еды; сытость, привязанность и задержка прежние. Правки во время еды действуют со следующего кормления. Старые профили нейтральны. Реакции food_like и food_dislike необязательны; готовые анимации ещё не созданы.',
    'Es': 'Cada mascota puede guardar una golosina favorita y otra distinta que le guste menos. Solo cambia el ánimo al completar la comida; saciedad, afecto y espera no cambian. Las ediciones durante la comida rigen en la siguiente. Los perfiles antiguos son neutros. food_like y food_dislike son opcionales; animaciones finales pendientes.',
    'Pt': 'Cada pet pode salvar um petisco favorito e outro diferente de que gosta menos. Só o humor muda após a refeição; saciedade, afeto e espera não mudam. Edições durante a refeição valem na próxima. Perfis antigos são neutros. food_like e food_dislike são opcionais; animações finais pendentes.',
    'Ja': 'ペットごとに好きなおやつと別の苦手なおやつを保存できます。食事完了後の気分だけに影響し、満腹度、好感度、待機時間は変わりません。食事中の変更は次回から有効です。旧セーブは好みなしです。food_like、food_dislikeは任意の反応で、正式アニメーションは未制作です。',
    'Ko': '펫마다 좋아하는 간식과 다른 싫어하는 간식을 저장할 수 있습니다. 식사 완료 후 기분에만 영향을 주며 포만감, 호감도, 대기 시간은 그대로입니다. 식사 중 변경은 다음 식사부터 적용됩니다. 기존 저장은 취향 없음입니다. food_like와 food_dislike 반응은 선택 사항이며 정식 애니메이션은 아직 없습니다.',
}
for filename, lang in files.items():
    path = root / filename
    text = path.read_text(encoding='utf-8')
    if lines[lang] not in text:
        path.write_text(text.rstrip() + '\n\n' + lines[lang] + '\n', encoding='utf-8', newline='\r\n')
