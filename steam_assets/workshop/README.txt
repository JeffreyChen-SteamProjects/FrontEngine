FrontEngine Workshop brand assets
Created: 2026-10-07
App ID: 2793470

Brand name: FrontEngine Workshop
Traditional Chinese name: FrontEngine 創意工坊
Tagline: Make your desktop yours.
Palette: charcoal #121415 / #1b1d1f, amber #ffd740, white.

Artwork uses the original FrontEngine app icon and the existing store asset style:
simple dark gradient, white title, amber Workshop label and short accent line.
These are programmatically rendered brand cards, not application screenshots.

Regenerate from the repository root:
    .venv\Scripts\python.exe steam_assets/generate_workshop.py

Files
- workshop_brand_landscape.png: 920 x 430 landscape PNG.
- workshop_brand_landscape.jpg: 920 x 430 landscape JPEG.
- workshop_preview_square.png: 512 x 512 square PNG.
- workshop_preview_square.jpg: 512 x 512 square JPEG.
- workshop_name.txt: name and bilingual taglines.
- workshop_description_zh-TW.txt: Traditional Chinese description.
- workshop_description_en.txt: English description.
- brand.json: reusable names, colors, status and image metadata.

The generator reuses helpers from steam_assets/generate.py and exe/frontengine.ico.
It replaces only the four Workshop images above and refreshes their brand.json metadata.
Existing store assets and bilingual copy remain unchanged.
All four images are below the project's conservative 1,000,000-byte preview limit.
JPEG files are encoded at quality 90.

The image sizes are layout choices; check the intended Steamworks field before upload.
Official preview API reference: https://partner.steamgames.com/doc/api/ISteamUGC#SetItemPreview

Descriptions disclose the current Workshop implementation status. Review that paragraph when the publishing and synchronization implementation ships.
Implementation plan: ../../docs/superpowers/plans/2026-10-07-steam-workshop.md
