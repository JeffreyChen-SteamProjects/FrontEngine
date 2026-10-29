from pathlib import Path
import json

root = Path(__file__).resolve().parents[2]
keys = 'title character head neck body back mirror preview outfits save wear delete none missing saved install unsupported'.split()
words = {
    'english': ['Wardrobe', 'Character', 'Head', 'Neck', 'Body', 'Back', 'Face left', 'Preview action', 'Saved outfits', 'Save new outfit', 'Wear selected', 'Delete selected', 'None', 'Missing', 'Appearance saved', 'Install asset folder', 'This model does not support layered sprite clothing'],
    'traditional_chinese': ['衣櫃', '角色', '頭部', '頸部', '身體', '背部', '朝左', '預覽動作', '收藏搭配', '另存新搭配', '穿上所選搭配', '刪除所選搭配', '無', '缺少素材', '已儲存外觀', '安裝素材資料夾', '此模型不支援 Sprite 分層服裝'],
    'simplified_chinese': ['衣柜', '角色', '头部', '颈部', '身体', '背部', '朝左', '预览动作', '收藏搭配', '另存新搭配', '穿上所选搭配', '删除所选搭配', '无', '缺少素材', '已保存外观', '安装素材文件夹', '此模型不支持 Sprite 分层服装'],
    'germany': ['Garderobe', 'Figur', 'Kopf', 'Hals', 'Körper', 'Rücken', 'Nach links', 'Animationsvorschau', 'Gespeicherte Outfits', 'Neues Outfit speichern', 'Auswahl anziehen', 'Auswahl löschen', 'Keine', 'Fehlt', 'Aussehen gespeichert', 'Asset-Ordner installieren', 'Dieses Modell unterstützt keine mehrschichtige Sprite-Kleidung'],
    'france': ['Garde-robe', 'Personnage', 'Tête', 'Cou', 'Corps', 'Dos', 'Vers la gauche', "Aperçu de l’action", 'Tenues enregistrées', 'Enregistrer une nouvelle tenue', 'Porter la sélection', 'Supprimer la sélection', 'Aucun', 'Manquant', 'Apparence enregistrée', 'Installer un dossier de ressources', 'Ce modèle ne prend pas en charge les vêtements Sprite en couches'],
    'italy': ['Guardaroba', 'Personaggio', 'Testa', 'Collo', 'Corpo', 'Schiena', 'Verso sinistra', 'Anteprima azione', 'Completi salvati', 'Salva nuovo completo', 'Indossa selezione', 'Elimina selezione', 'Nessuno', 'Mancante', 'Aspetto salvato', 'Installa cartella risorse', 'Questo modello non supporta abiti Sprite a livelli'],
    'russian': ['Гардероб', 'Персонаж', 'Голова', 'Шея', 'Тело', 'Спина', 'Влево', 'Просмотр действия', 'Сохранённые наряды', 'Сохранить новый наряд', 'Надеть выбранное', 'Удалить выбранное', 'Нет', 'Отсутствует', 'Внешность сохранена', 'Установить папку ресурсов', 'Эта модель не поддерживает многослойную одежду Sprite'],
}
for language, values in words.items():
    assert len(keys) == len(values)
    path = root / 'frontengine/utils/multi_language' / (language + '.py')
    text = path.read_text(encoding='utf-8')
    if "'pet_wardrobe_title'" not in text:
        index = text.rfind('}')
        addition = ''.join('    ' + repr('pet_wardrobe_' + key) + ': ' + json.dumps(value, ensure_ascii=False) + ',\n' for key, value in zip(keys, values))
        path.write_text(text[:index] + addition + text[index:], encoding='utf-8', newline='\n')

updates = dict(zip(words, ['Update selected', '更新所選搭配', '更新所选搭配', 'Auswahl aktualisieren',
                          'Mettre à jour la sélection', 'Aggiorna selezione', 'Обновить выбранное']))
for language, value in updates.items():
    path = root / 'frontengine/utils/multi_language' / (language + '.py')
    text = path.read_text(encoding='utf-8')
    if "'pet_wardrobe_update'" not in text:
        index = text.rfind('}')
        text = text[:index] + "    'pet_wardrobe_update': " + json.dumps(value, ensure_ascii=False) + ',\n' + text[index:]
        path.write_text(text, encoding='utf-8', newline='\n')

labels = {
    'english': ['Outfit name', 'Refresh assets'],
    'traditional_chinese': ['搭配名稱', '重新掃描素材'],
    'simplified_chinese': ['搭配名称', '重新扫描素材'],
    'germany': ['Outfit-Name', 'Assets aktualisieren'],
    'france': ['Nom de la tenue', 'Actualiser les ressources'],
    'italy': ['Nome completo', 'Aggiorna risorse'],
    'russian': ['Название наряда', 'Обновить ресурсы'],
}
for language, values in labels.items():
    path = root / 'frontengine/utils/multi_language' / (language + '.py')
    text = path.read_text(encoding='utf-8')
    for suffix, value in zip(('name', 'refresh'), values):
        key = 'pet_wardrobe_' + suffix
        if repr(key) not in text:
            index = text.rfind('}')
            text = text[:index] + '    ' + repr(key) + ': ' + json.dumps(value, ensure_ascii=False) + ',\n' + text[index:]
    path.write_text(text, encoding='utf-8', newline='\n')

paragraphs = {
'Eng': 'Pet identities → Wardrobe opens a separate animated preview for an installed layered character. Install asset folder copies validated layered-pet.json resources into pet-assets beside the local settings. Choose head, neck, body and back items, preview actions and facing, and save up to 20 outfits per identity. Unequip a conflicting item before equipping another. Apply saves and updates the active sprite; Cancel discards edits since the last Apply. Missing resources remain referenced and can be repaired, then rescanned with Refresh. Puppet models do not accept layered Sprite clothing. No built-in finished layered character artwork is included yet.',
'Zh': '寵物身分 → 衣櫃可預覽已安裝的分層角色。安裝素材資料夾會驗證 layered-pet.json 並複製到本機設定旁的 pet-assets。可選頭、頸、身體、背部配件，預覽動作與朝向，每個體最多收藏 20 套搭配。槽位衝突時先卸下原配件。套用會保存並更新正在顯示的 Sprite；取消捨棄上次套用後的編輯。缺少素材仍保留引用，修復後按重新整理。Puppet 不使用 Sprite 分層衣服。目前尚未附帶完成的內建分層角色美術。',
'ZhCn': '宠物身份 → 衣柜可预览已安装的分层角色。安装素材文件夹会验证 layered-pet.json 并复制到本地设置旁的 pet-assets。可选头、颈、身体、背部配件，预览动作与朝向，每个体最多收藏 20 套搭配。槽位冲突时先卸下原配件。应用会保存并更新正在显示的 Sprite；取消放弃上次应用后的编辑。缺少素材仍保留引用，修复后按刷新。Puppet 不使用 Sprite 分层衣服。目前尚未附带完成的内置分层角色美术。',
'De': 'Tieridentitäten → Garderobe öffnet eine eigene animierte Vorschau installierter Figuren. Asset-Ordner installieren prüft layered-pet.json und kopiert Ressourcen nach pet-assets neben den lokalen Einstellungen. Kopf, Hals, Körper und Rücken, Aktionen und Blickrichtung sind wählbar; jede Identität speichert bis zu 20 Outfits. Bei Konflikten zuerst das bisherige Teil ablegen. Anwenden speichert und aktualisiert das aktive Sprite; Abbrechen verwirft Änderungen seit dem letzten Anwenden. Fehlende Ressourcen bleiben referenziert und können nach Reparatur neu eingelesen werden. Puppet unterstützt diese Sprite-Kleidung nicht. Fertige eingebaute mehrschichtige Figuren sind noch nicht enthalten.',
'Fr': 'Identités des animaux → Garde-robe ouvre un aperçu animé distinct des personnages installés. Installer un dossier vérifie layered-pet.json et copie les ressources dans pet-assets près des paramètres locaux. Choisissez les éléments de tête, cou, corps et dos, les actions et la direction, puis enregistrez jusqu’à 20 tenues par identité. Retirez d’abord les éléments en conflit. Appliquer enregistre et actualise le Sprite actif ; Annuler abandonne les modifications depuis la dernière application. Les ressources manquantes restent référencées ; réparez-les puis actualisez. Puppet ne prend pas en charge ces vêtements Sprite. Aucun personnage multicouche intégré finalisé n’est encore inclus.',
'It': 'Identità animali → Guardaroba apre un’anteprima animata separata dei personaggi installati. Installa cartella risorse verifica layered-pet.json e copia le risorse in pet-assets accanto alle impostazioni locali. Scegli testa, collo, corpo e schiena, azioni e direzione; salva fino a 20 completi per identità. Rimuovi prima gli elementi in conflitto. Applica salva e aggiorna lo Sprite attivo; Annulla scarta le modifiche dopo l’ultima applicazione. I riferimenti mancanti restano salvati: ripara le risorse e aggiorna. Puppet non supporta questi abiti Sprite. Non sono ancora inclusi personaggi multistrato integrati completi.',
'Ru': 'Идентичности питомцев → Гардероб открывает отдельный анимированный просмотр установленных персонажей. Установка папки проверяет layered-pet.json и копирует ресурсы в pet-assets рядом с локальными настройками. Выбирайте предметы для головы, шеи, тела и спины, действие и направление; сохраняйте до 20 нарядов на питомца. Сначала снимите конфликтующий предмет. Применить сохраняет и обновляет активный Sprite; Отмена сбрасывает изменения после последнего применения. Ссылки на отсутствующие ресурсы сохраняются: восстановите файлы и обновите список. Puppet не поддерживает эту одежду Sprite. Готовые встроенные многослойные персонажи пока не включены.',
}
readmes = {'README.md':'Eng', 'README/README_zh-TW.md':'Zh', 'README/README_zh-CN.md':'ZhCn', 'README/README_de.md':'De', 'README/README_fr.md':'Fr', 'README/README_ru.md':'Ru'}
extra = {
'README/README_es.md': 'Identidades de mascotas → Armario abre una vista previa animada independiente. Instalar carpeta valida layered-pet.json y copia los recursos a pet-assets junto a la configuración local. Elige cabeza, cuello, cuerpo y espalda, acción y orientación; guarda hasta 20 conjuntos por mascota. Quita primero los elementos incompatibles. Aplicar guarda y actualiza el Sprite activo; Cancelar descarta los cambios desde la última aplicación. Las referencias ausentes se conservan: repara los archivos y actualiza. Puppet no admite esta ropa Sprite. Todavía no se incluyen personajes integrados completos por capas.',
'README/README_pt-BR.md': 'Identidades dos pets → Guarda-roupa abre uma prévia animada separada. Instalar pasta valida layered-pet.json e copia os recursos para pet-assets junto das configurações locais. Escolha cabeça, pescoço, corpo e costas, ação e direção; salve até 20 conjuntos por pet. Remova primeiro os itens em conflito. Aplicar salva e atualiza o Sprite ativo; Cancelar descarta alterações desde a última aplicação. Referências ausentes são preservadas: repare os arquivos e atualize. Puppet não aceita essas roupas Sprite. Ainda não há personagens integrados completos em camadas.',
'README/README_ja.md': 'ペットの個体設定 → ワードローブで独立したアニメーションプレビューを開けます。素材フォルダーのインストールは layered-pet.json を検証し、設定の隣の pet-assets にコピーします。頭・首・胴体・背中の装備、動作、向きを選び、個体ごとに最大 20 組を保存できます。競合する装備は先に外してください。適用で保存して表示中の Sprite を更新し、キャンセルで前回の適用後の編集を破棄します。欠損素材の参照は保持され、修復後に更新できます。Puppet はこの Sprite 衣装に対応しません。完成した内蔵レイヤーキャラクター素材はまだ含まれません。',
'README/README_ko.md': '펫 개체 설정 → 옷장에서 별도의 애니메이션 미리보기를 엽니다. 소재 폴더 설치는 layered-pet.json을 검증하고 로컬 설정 옆 pet-assets에 복사합니다. 머리·목·몸·등 장비, 동작과 방향을 선택하고 개체마다 최대 20개 조합을 저장합니다. 충돌하는 장비는 먼저 벗겨야 합니다. 적용하면 저장하고 활성 Sprite를 갱신하며, 취소하면 마지막 적용 이후 편집을 버립니다. 누락된 소재 참조는 보존되므로 파일을 복구한 뒤 새로 고칠 수 있습니다. Puppet은 이 Sprite 의상을 지원하지 않습니다. 완성된 내장 레이어 캐릭터 소재는 아직 포함되지 않습니다.',
}
targets = {root / file: paragraphs[lang] for file, lang in readmes.items()}
targets.update({root / file: value for file, value in extra.items()})
targets.update({root / 'docs/source/docs' / lang / 'pet.rst': value for lang, value in paragraphs.items()})
for path, paragraph in targets.items():
    text = path.read_text(encoding='utf-8')
    if paragraph not in text:
        path.write_text(text.rstrip() + '\n\n' + paragraph + '\n', encoding='utf-8', newline='\r\n')

obsolete = [
    'Validated appearance references are saved, but this release has no wardrobe, layered artwork or toy interface.',
    'Appearance references do not provide a wardrobe or layered artwork in this release.',
    '存檔保存經驗證的外觀引用，本版尚無衣櫃、分層美術或玩具介面。',
    '本版尚未提供衣櫃或分層美術，外觀引用不代表已具備換裝功能。',
    '存档保存经过验证的外观引用，本版尚无衣柜、分层美术或玩具界面。',
    '本版尚未提供衣柜或分层美术，外观引用不代表已具备换装功能。',
    'Geprüfte Aussehensverweise werden gespeichert; Garderobe, Ebenengrafik und Spielzeugoberfläche fehlen noch.',
    'Diese Version enthält noch keine Garderobe oder Grafik mit mehreren Ebenen.',
    'Les références d’apparence sont validées et enregistrées ; garde-robe, graphismes en couches et interface de jouets ne sont pas encore inclus.',
    'Cette version ne fournit pas encore de garde-robe ni de graphismes en couches.',
    'Questa versione non include ancora un guardaroba o grafica a livelli.',
    'Проверенные ссылки на внешность сохраняются; гардероба, многослойной графики и интерфейса игрушек пока нет.',
    'В этой версии ещё нет гардероба или многослойной графики.',
    'Referências de aparência são validadas e salvas; ainda não há guarda-roupa, arte em camadas ou interface de brinquedos.',
    'Se guardan referencias de apariencia validadas; aún no hay vestuario, gráficos por capas ni interfaz de juguetes.',
    '検証済みの外観参照を保存しますが、衣装庫、レイヤー画像、おもちゃ画面は未実装です。',
    '검증한 외형 참조를 저장하지만 옷장, 레이어 그림, 장난감 화면은 아직 제공하지 않습니다.',
]
for path in targets:
    text = path.read_text(encoding='utf-8')
    for sentence in obsolete:
        text = text.replace(sentence, '')
    path.write_text(text, encoding='utf-8', newline='\r\n')
