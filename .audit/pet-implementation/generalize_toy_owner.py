from pathlib import Path

root = Path(__file__).resolve().parents[2]
for filename in ('frontengine/show/pet/desktop_pet.py', 'frontengine/show/pet/ball_toy.py',
                 'tests/unit_test/test_pet_ball.py'):
    path = root / filename
    text = path.read_text(encoding='utf-8')
    for old, new in (('self._ball', 'self._toy'), ('pet._ball', 'pet._toy'),
                     ('stop_ball', 'stop_toy'), ('can_play_ball', 'can_play_with_toy')):
        text = text.replace(old, new)
    path.write_text(text, encoding='utf-8', newline='\r\n')
