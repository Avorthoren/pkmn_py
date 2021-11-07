from enum import Enum

from pkmn_stat import StatType


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
	BRAVE   = NatureData(StatType.ATK,   StatType.SPATK)
	ADAMANT = NatureData(StatType.ATK,   StatType.SPDEF)
	NAUGHTY = NatureData(StatType.ATK,   StatType.SPEED)

	BOLD    = NatureData(StatType.DEF,   StatType.ATK)
	DOCILE  = NatureData(StatType.DEF,   StatType.DEF)
	RELAXED = NatureData(StatType.DEF,   StatType.SPATK)
	IMPISH  = NatureData(StatType.DEF,   StatType.SPDEF)
	LAX     = NatureData(StatType.DEF,   StatType.SPEED)

	TIMID   = NatureData(StatType.SPATK, StatType.ATK)
	HASTY   = NatureData(StatType.SPATK, StatType.DEF)
	SERIOUS = NatureData(StatType.SPATK, StatType.SPATK)
	JOLLY   = NatureData(StatType.SPATK, StatType.SPDEF)
	NAIVE   = NatureData(StatType.SPATK, StatType.SPEED)

	MODEST  = NatureData(StatType.SPDEF, StatType.ATK)
	MILD    = NatureData(StatType.SPDEF, StatType.DEF)
	QUIET   = NatureData(StatType.SPDEF, StatType.SPATK)
	BASHFUL = NatureData(StatType.SPDEF, StatType.SPDEF)
	RASH    = NatureData(StatType.SPDEF, StatType.SPEED)

	CALM    = NatureData(StatType.SPEED, StatType.ATK)
	GENTLE  = NatureData(StatType.SPEED, StatType.DEF)
	SASSY   = NatureData(StatType.SPEED, StatType.SPATK)
	CAREFUL = NatureData(StatType.SPEED, StatType.SPDEF)
	QUIRKY  = NatureData(StatType.SPEED, StatType.SPEED)

	DEFAULT = HARDY  # Convenient


def main():
	print(Nature.ADAMANT.is_simple())


if __name__ == "__main__":
	main()

