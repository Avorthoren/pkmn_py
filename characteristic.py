from enum import Enum

from pkmn_stat_type import StatType


class CharacteristicData:
	# Characteristic is a pair of `stat_type` and `remainder` modulo `MOD`
	# It implies that `stat_type` has the highest iv value among other stat
	# types, and this value modulo `MOD` equals `reminder`.
	# There is rule for ties in iv values for different stats, but it requires
	# Pokémon's personality value:
	# https://bulbapedia.bulbagarden.net/wiki/Characteristic#Ties
	MOD = 5

	def __init__(self, highest_stat: StatType, rem: int):
		self._highest_stat = highest_stat
		self._rem = rem

	@property
	def highest_stat(self) -> StatType:
		return self._highest_stat

	@property
	def rem(self) -> int:
		return self._rem


class Characteristic(Enum):
	@property
	def highest_stat(self) -> StatType:
		return self.value.highest_stat

	@property
	def rem(self) -> int:
		return self.value.rem

	LOVES_TO_EAT            = CharacteristicData(StatType.HP,    0)
	PROUD_OF_ITS_POWER      = CharacteristicData(StatType.ATK,   0)
	STURDY_BODY             = CharacteristicData(StatType.DEF,   0)
	HIGHLY_CURIOUS          = CharacteristicData(StatType.SPATK, 0)
	STRONG_WILLED           = CharacteristicData(StatType.SPDEF, 0)
	LIKES_TO_RUN            = CharacteristicData(StatType.SPEED, 0)

	TAKES_PLENTY_OF_SIESTAS = CharacteristicData(StatType.HP,    1)
	OFTEN_DOZES_OFF = TAKES_PLENTY_OF_SIESTAS  # legacy
	LIKES_TO_TRASH_ABOUT    = CharacteristicData(StatType.ATK,   1)
	CAPABLE_OF_TAKING_HITS  = CharacteristicData(StatType.DEF,   1)
	MISCHIEVOUS             = CharacteristicData(StatType.SPATK, 1)
	SOMEWHAT_VAIN           = CharacteristicData(StatType.SPDEF, 1)
	ALERT_TO_SOUNDS         = CharacteristicData(StatType.SPEED, 1)

	NODS_OFF_A_LOT          = CharacteristicData(StatType.HP,    2)
	OFTEN_SCATTERS_THINGS = NODS_OFF_A_LOT  # legacy
	A_LITTLE_QUICK_TEMPERED = CharacteristicData(StatType.ATK,   2)
	HIGHLY_PERSISTENT       = CharacteristicData(StatType.DEF,   2)
	THOROUGHLY_CUNNING      = CharacteristicData(StatType.SPATK, 2)
	STRONGLY_DEFIANT        = CharacteristicData(StatType.SPDEF, 2)
	IMPETUOUS_AND_SILLY     = CharacteristicData(StatType.SPEED, 2)

	SCATTERS_THINGS_OFTEN   = CharacteristicData(StatType.HP,    3)
	LIKES_TO_FIGHT          = CharacteristicData(StatType.ATK,   3)
	GOOD_ENDURANCE          = CharacteristicData(StatType.DEF,   3)
	OFTEN_LOST_IN_THOUGHT   = CharacteristicData(StatType.SPATK, 3)
	HATES_TO_LOSE           = CharacteristicData(StatType.SPDEF, 3)
	SOMEWHAT_OF_CLOWN       = CharacteristicData(StatType.SPEED, 3)

	LIKES_TO_RELAX          = CharacteristicData(StatType.HP,    4)
	QUICK_TEMPERED          = CharacteristicData(StatType.ATK,   4)
	GOOD_PERSEVERANCE       = CharacteristicData(StatType.DEF,   4)
	VERY_FINICKY            = CharacteristicData(StatType.SPATK, 4)
	SOMEWHAT_STUBBORN       = CharacteristicData(StatType.SPDEF, 4)
	QUICK_TO_FLEE           = CharacteristicData(StatType.SPEED, 4)
