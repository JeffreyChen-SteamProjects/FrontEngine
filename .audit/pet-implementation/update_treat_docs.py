import json
from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
labels = {
    'english': ['Treats', 'Crunchy bite', 'Hearty bowl', 'Melody biscuit', 'Page wafer'],
    'traditional_chinese': ['選點心', '香脆小點', '滿滿大餐', '旋律餅乾', '書頁薄餅'],
    'simplified_chinese': ['选点心', '香脆小点', '满满大餐', '旋律饼干', '书页薄饼'],
    'germany': ['Leckerbissen', 'Knusperhappen', 'Herzhafte Schale', 'Melodiekeks', 'Buchseitenwaffel'],
    'france': ['Friandises', 'Bouchée croquante', 'Bol copieux', 'Biscuit mélodique', 'Gaufrette de page'],
    'italy': ['Spuntini', 'Boccone croccante', 'Ciotola abbondante', 'Biscotto melodico', 'Cialda a pagina'],
    'russian': ['Угощения', 'Хрустящий кусочек', 'Сытная миска', 'Музыкальное печенье', 'Вафельная страничка'],
}
keys = ['pet_treats', 'pet_treat_snack', 'pet_treat_feast', 'pet_treat_music', 'pet_treat_book']
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
    'Eng': 'Sprite and Puppet menus now offer four fictional treats without requiring a file drop. They share feeding completion, fullness limits and cooldowns. Feeding ends petting first; unfinished petting gives no reward, and Sprite toys are put away.',
    'Zh': 'Sprite 與 Puppet 選單可直接選四種虛構點心，不必拖放檔案；沿用餵食完成、飽足上限與冷卻規則。餵食前結束撫摸，未完成撫摸不給獎勵，Sprite 同時收起玩具。',
    'ZhCn': 'Sprite 与 Puppet 菜单可直接选四种虚构点心，不必拖放文件；沿用喂食完成、饱足上限与冷却规则。喂食前结束抚摸，未完成抚摸不给奖励，Sprite 同时收起玩具。',
    'De': 'Sprite- und Puppet-Menüs bieten vier fiktive Leckerbissen ohne Dateiablage. Abschluss, Sättigungsgrenze und Wartezeit bleiben gemeinsam. Füttern beendet Streicheln ohne Belohnung für unvollständige Gesten; Sprite räumt Spielzeug weg.',
    'Fr': 'Les menus Sprite et Puppet proposent quatre friandises fictives sans déposer de fichier. Fin du repas, satiété et délai restent communs. Nourrir termine la caresse sans récompense si elle est inachevée ; Sprite range son jouet.',
    'It': 'I menu Sprite e Puppet offrono quattro spuntini immaginari senza trascinare file. Completamento, sazietà e attesa restano condivisi. Nutrire interrompe la carezza incompleta senza premio; Sprite ripone il giocattolo.',
    'Ru': 'Меню Sprite и Puppet предлагают четыре вымышленных угощения без перетаскивания файлов. Завершение кормления, предел сытости и задержка общие. Кормление прерывает незавершённое поглаживание без награды; Sprite убирает игрушку.',
    'Es': 'Los menús Sprite y Puppet ofrecen cuatro golosinas ficticias sin arrastrar archivos. Comparten finalización, límite de saciedad y espera. Alimentar termina la caricia incompleta sin recompensa; Sprite guarda el juguete.',
    'Pt': 'Os menus Sprite e Puppet oferecem quatro petiscos fictícios sem arrastar arquivos. Compartilham conclusão, limite de saciedade e espera. Alimentar encerra o carinho incompleto sem recompensa; Sprite guarda o brinquedo.',
    'Ja': 'SpriteとPuppetのメニューで、ファイルを渡さずに4種類の架空のおやつを選べます。食事の完了、満腹制限、待機時間は共通です。餌やり前に撫でる操作を終了し、未完了分の報酬は与えず、Spriteのおもちゃも片付けます。',
    'Ko': 'Sprite와 Puppet 메뉴에서 파일을 끌어 놓지 않고 네 가지 가상 간식을 선택할 수 있습니다. 완료, 포만감 제한, 대기 시간을 공유합니다. 먹이 주기는 미완료 쓰다듬기를 보상 없이 끝내고 Sprite 장난감도 치웁니다.',
}
for filename, lang in files.items():
    path = root / filename
    text = path.read_text(encoding='utf-8')
    if lines[lang] not in text:
        path.write_text(text.rstrip() + '\n\n' + lines[lang] + '\n', encoding='utf-8', newline='\r\n')
