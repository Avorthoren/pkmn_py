from enum import Enum

from pkmn_stat_type import StatType


class NatureData:
	def __init__(self, increased: StatType, decreased: StatType):
		self._increased = increased
		self._decreased = decreased

	@property
	def increased(self) -> StatType:
		return self._increased

	@property
	def decreased(self) -> StatType:
		return self._decreased

	def is_simple(self) -> bool:
		return self.increased == self.decreased


class Nature(Enum):
	@property
	def increased(self) -> StatType:
		return self.value.increased

	@property
	def decreased(self) -> StatType:
		return self.value.decreased

	def is_simple(self) -> bool:
		return self.value.is_simple()

	HARDY   = NatureData(StatType.ATK,   StatType.ATK)
	LONELY  = NatureData(StatType.ATK,   StatType.DEF)
	ADAMANT = NatureData(StatType.ATK,   StatType.SPATK)
	NAUGHTY = NatureData(StatType.ATK,   StatType.SPDEF)
	BRAVE   = NatureData(StatType.ATK,   StatType.SPEED)

	BOLD    = NatureData(StatType.DEF,   StatType.ATK)
	DOCILE  = NatureData(StatType.DEF,   StatType.DEF)
	IMPISH  = NatureData(StatType.DEF,   StatType.SPATK)
	LAX     = NatureData(StatType.DEF,   StatType.SPDEF)
	RELAXED = NatureData(StatType.DEF,   StatType.SPEED)

	MODEST  = NatureData(StatType.SPATK, StatType.ATK)
	MILD    = NatureData(StatType.SPATK, StatType.DEF)
	BASHFUL = NatureData(StatType.SPATK, StatType.SPATK)
	RASH    = NatureData(StatType.SPATK, StatType.SPDEF)
	QUIET   = NatureData(StatType.SPATK, StatType.SPEED)

	CALM    = NatureData(StatType.SPDEF, StatType.ATK)
	GENTLE  = NatureData(StatType.SPDEF, StatType.DEF)
	CAREFUL = NatureData(StatType.SPDEF, StatType.SPATK)
	QUIRKY  = NatureData(StatType.SPDEF, StatType.SPDEF)
	SASSY   = NatureData(StatType.SPDEF, StatType.SPEED)

	TIMID   = NatureData(StatType.SPEED, StatType.ATK)
	HASTY   = NatureData(StatType.SPEED, StatType.DEF)
	JOLLY   = NatureData(StatType.SPEED, StatType.SPATK)
	NAIVE   = NatureData(StatType.SPEED, StatType.SPDEF)
	SERIOUS = NatureData(StatType.SPEED, StatType.SPEED)

	DEFAULT = HARDY  # Convenient


def main():
	print(Nature.ADAMANT.is_simple())


if __name__ == "__main__":
	main()

