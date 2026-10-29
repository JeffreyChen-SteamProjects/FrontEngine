"""Qt-free pet care values and food effects."""

MAX_AFFECTION = 1000000

FOOD_SNACK = "snack"    # 一般點心 / an ordinary snack


FOOD_FEAST = "feast"    # 壓縮檔＝大餐 / an archive is a hearty meal


FOOD_MUSIC = "music"    # 音樂檔＝聽了很開心 / music cheers it up more than it fills


FOOD_BOOK = "book"      # 文件檔＝細嚼慢嚥 / a document is chewed slowly


FOOD_HARD = "hard"      # 可執行檔＝咬不動 / a binary is too hard to chew

TREAT_KINDS = (FOOD_SNACK, FOOD_FEAST, FOOD_MUSIC, FOOD_BOOK)


FOOD_EFFECTS = {
    FOOD_SNACK: {"fullness": 30, "mood": 12, "affection": 5},
    FOOD_FEAST: {"fullness": 45, "mood": 8, "affection": 6},
    FOOD_MUSIC: {"fullness": 15, "mood": 20, "affection": 5},
    FOOD_BOOK: {"fullness": 20, "mood": 6, "affection": 4},
    FOOD_HARD: {"fullness": 2, "mood": -6, "affection": 1},
}


class PetMood:
    """
    寵物心情值 0~100：互動會上升、被忽略會慢慢下降；level() 回傳 happy/content/sad。
    Pet happiness 0..100: petting raises it, neglect decays it; level() buckets it.
    """

    HAPPY = "happy"
    CONTENT = "content"
    SAD = "sad"

    def __init__(self, value: int = 60) -> None:
        self.value = self._clamp(value)

    @staticmethod
    def _clamp(value) -> int:
        try:
            return max(0, min(100, int(value)))
        except (TypeError, ValueError):
            return 60

    def pet(self, amount: int = 12) -> None:
        self.value = self._clamp(self.value + amount)

    def decay(self, amount: int = 1) -> None:
        self.value = self._clamp(self.value - amount)

    def level(self) -> str:
        if self.value >= 70:
            return self.HAPPY
        if self.value <= 30:
            return self.SAD
        return self.CONTENT


class PetGrowth:
    """
    親密度累積與等級：互動會累加親密度，跨過門檻即升級。
    Affection points accrue from interactions; crossing a threshold levels up.
    """

    THRESHOLDS = (0, 100, 250, 500, 1000, 2000)

    def __init__(self, affection: int = 0) -> None:
        self.affection = self._clamp(affection)

    @staticmethod
    def _clamp(value) -> int:
        try:
            return max(0, min(MAX_AFFECTION, int(value)))
        except (TypeError, ValueError, OverflowError):
            return 0

    def level(self) -> int:
        return max(1, sum(1 for threshold in self.THRESHOLDS if self.affection >= threshold))

    def add(self, amount: int) -> bool:
        """累加親密度；若因此升級回傳 True。"""
        before = self.level()
        self.affection = self._clamp(self.affection + int(amount))
        return self.level() > before


# Relationship stages shown to the user. They only add greeting variants and a
# keepsake celebration; nothing is ever lost or locked away from the user.
BOND_STAGES = (("new", 0), ("familiar", 20), ("close", 100), ("in_sync", 250))


def bond_stage(affection: int) -> str:
    stage = BOND_STAGES[0][0]
    for name, threshold in BOND_STAGES:
        if affection >= threshold:
            stage = name
    return stage


class PetHunger:
    """
    寵物飽足值 0~100：餵食上升、隨時間下降；level() 回傳 full/ok/hungry。
    Pet fullness 0..100: feeding raises it, time lowers it; level() buckets it.
    """

    FULL = "full"
    OK = "ok"
    HUNGRY = "hungry"

    def __init__(self, value: int = 70) -> None:
        self.value = self._clamp(value)

    @staticmethod
    def _clamp(value) -> int:
        try:
            return max(0, min(100, int(value)))
        except (TypeError, ValueError):
            return 70

    def feed(self, amount: int = 30) -> None:
        self.value = self._clamp(self.value + amount)

    def decay(self, amount: int = 1) -> None:
        self.value = self._clamp(self.value - amount)

    def level(self) -> str:
        if self.value >= 60:
            return self.FULL
        if self.value <= 25:
            return self.HUNGRY
        return self.OK
