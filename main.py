from enum import Enum
import math

MAX_CATCH_RATE = 255
TRASH_HOLD_RANGE = 256**2
CRITICAL_CAPTURE_TRASH_HOLD_RANGE = 256
SHAKES = 4


def prob(catchRate, hpRate=1., ballBonus=1., statusBonus=1., criticalCaptureRate=0.):
	modifiedCatchRate = catchRate * (1 - 2/3 * hpRate) * ballBonus * statusBonus
	trashHold = int(TRASH_HOLD_RANGE / (MAX_CATCH_RATE / modifiedCatchRate) ** 0.1875)
	shakeSuccProb = min(trashHold / TRASH_HOLD_RANGE, 1.0)
	captureProb = shakeSuccProb ** SHAKES

	criticalCaptureTrashHold = int(modifiedCatchRate * criticalCaptureRate / 6)
	criticalCaptureProb = min(criticalCaptureTrashHold / CRITICAL_CAPTURE_TRASH_HOLD_RANGE, 1.0)

	return (1 - criticalCaptureProb) * captureProb + criticalCaptureProb * shakeSuccProb


# print(prob(
# 	catchRate=255,
# 	hpRate=1/48,
# 	# ballBonus=1.5,
# 	# statusBonus=2,
# 	criticalCaptureRate=0.5
# ))


def clamp(x, min_=None, max_=None):
	if min_ is not None:
		x = max(min_, x)
	if max_ is not None:
		x = min(x, max_)

	return x


class StatType(Enum):
	HP = 1
	ATK = 2
	DEF = 3
	SPATK = 4
	SPDEF = 5
	SPEED = 6


class NatureData:
	def __init__(self, increased, decreased):
		self._increased = increased
		self._decreased = decreased

	@property
	def increased(self):
		return self._increased

	@property
	def decreased(self):
		return self._decreased


class Nature(Enum):
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


class CharacteristicData:
	def __init__(self, highestStat, rem):
		self._highestStat = highestStat
		self._rem = rem

	@property
	def highestStat(self):
		return self._highestStat

	@property
	def rem(self):
		return self._rem


class Characteristic(Enum):
	LOVES_TO_EAT            = CharacteristicData(StatType.HP,    0)
	PROUD_OF_ITS_POWER      = CharacteristicData(StatType.ATK,   0)
	STURDY_BODY             = CharacteristicData(StatType.DEF,   0)
	HIGHLY_CURIOUS          = CharacteristicData(StatType.SPATK, 0)
	STRONG_WILLED           = CharacteristicData(StatType.SPDEF, 0)
	LIKES_TO_RUN            = CharacteristicData(StatType.SPEED, 0)

	TAKES_PLENTY_OF_SIESTAS = CharacteristicData(StatType.HP,    1)
	LIKES_TO_TRASH_ABOUT    = CharacteristicData(StatType.ATK,   1)
	CAPABLE_OF_TAKING_HITS  = CharacteristicData(StatType.DEF,   1)
	MISCHIEVOUS             = CharacteristicData(StatType.SPATK, 1)
	SOMEWHAT_VAIN           = CharacteristicData(StatType.SPDEF, 1)
	ALERT_TO_SOUNDS         = CharacteristicData(StatType.SPEED, 1)

	NODS_OFF_A_LOT          = CharacteristicData(StatType.HP,    2)
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


class Stat:
	_MIN_VALUE = 0
	_MAX_VALUE = 31

	@classmethod
	def clamp(cls, val):
		return clamp(val, cls._MIN_VALUE, cls._MAX_VALUE)

	def __init__(self, type_, base, lvl=None, val=None, iv=None, ev=0, mult=1.0):
		self._type = type_
		self._base = base
		self._lvl = lvl
		self._val = val
		self._iv = iv
		self._ev = ev
		self._mult = mult

	def getVal(self, lvl=None):
		if lvl is None:
			if self._lvl is None:
				raise ValueError("Lvl must be specified")

			if self._val is not None:
				return self._val

			lvl = self._lvl

		if self._iv is None:
			raise ValueError("IV must be specified")

		if self._type == StatType.HP:
			return (2*self._base + self._iv + self._ev//4) * lvl // 100 + lvl + 10
		else:
			return math.floor(((2 * self._base + self._iv + self._ev // 4) * lvl // 100 + 5) * self._mult)

	@classmethod
	def min_(cls, left, mult):
		res = int(left / mult)
		if int(res * mult) == left:
			return res
		elif int((res + 1) * mult) == left:
			return res + 1
		else:
			raise Exception("min_() implementation error")

	@classmethod
	def max_(cls, left, mult):
		res = int((left + 1) / mult)
		if int(res * mult) == left:
			return res
		elif int((res - 1) * mult) == left:
			return res - 1
		else:
			raise Exception("max_() implementation error")

	@classmethod
	def range_(cls, left, mult):
		return cls.min_(left, mult), cls.max_(left, mult)

	@staticmethod
	def rangeMerge(r1, r2):
		return min(r1[0], r2[0]), max(r1[1], r2[1])
	
	def getIVRange(self):
		if self._lvl is None:
			raise ValueError("Lvl must be specified")
		if self._val is None:
			raise ValueError("Stat value must be specified")

		if self._type == StatType.HP:
			left = self._val - 10 - self._lvl
			range_ = left, left
		else:
			range_ = self.range_(self._val, self._mult)
			range_ = range_[0] - 5, range_[1] - 5

		range_ = self.rangeMerge(
			self.range_(range_[0], self._lvl/100),
			self.range_(range_[1], self._lvl/100)
		)

		baseAndEV = 2*self._base + self._ev//4
		range_ = range_[0] - baseAndEV, range_[1] - baseAndEV

		if range_[0] > self._MAX_VALUE or range_[1] < self._MIN_VALUE:
			raise ValueError(f"Calculated {self._type.name} IVs are impossible: [{range_[0]}, {range_[1]}]")

		return self.clamp(range_[0]), self.clamp(range_[1])


class Species:
	def __init__(self, name, catchRate, baseStats):
		self._name = name
		self._catchRate = catchRate
		self._stats = {
			type_: Stat(type_, base=baseStats[type_])
			for type_ in StatType
		}


class Pokemon(Enum):
	MAGIKARP = Species("Magikarp", catchRate=255, baseStats={
		StatType.HP: 20,
		StatType.ATK: 10,
		StatType.DEF: 55,
		StatType.SPATK: 15,
		StatType.SPDEF: 20,
		StatType.SPEED: 80
	})


class Representative(Species):
	def __init__(self, spec, nature=None, characteristic=None, lvl=None, stats=None):
		if nature is None:
			raise NotImplementedError

		super().__init__(spec.value._name, spec.value._catchRate, {
			type_: spec.value._stats[type_]._base
			for type_ in StatType
		})

		self._nature = nature
		self._characteristic = characteristic
		self._lvl = lvl

		for type_ in StatType:
			self._stats[type_]._lvl = lvl
			if stats is not None:
				self._stats[type_]._val = stats[type_].get("value")
				self._stats[type_]._iv = stats[type_].get("iv")
				self._stats[type_]._ev = stats[type_].get("ev", 0)
				if nature.value.increased != nature.value.decreased:
					if type_ == nature.value.increased:
						self._stats[type_]._mult = 1.1
					elif type_ == nature.value.decreased:
						self._stats[type_]._mult = 0.9

	def getIVSets(self):
		if self._lvl is None:
			raise NotImplementedError

		ranges = {
			type_: self._stats[type_].getIVRange()
			for type_ in StatType
		}

		sets = {
			type_: set(range(range_[0], range_[1] + 1))
			for type_, range_ in ranges.items()
		}

		if self._characteristic is not None:
			highestStat, rem = self._characteristic.value._highestStat, self._characteristic.value._rem
			sets[highestStat] = {val for val in sets[highestStat] if val % 5 == rem}
			if not sets[highestStat]:
				raise ValueError(f"This {self._name} has impossible input values")

			for type_, set_ in sets.items():
				if type_ != highestStat:
					sets[type_] = {val for val in sets[type_] if val <= max(sets[highestStat])}
					if not sets[type_]:
						raise ValueError(f"This {self._name} has impossible input values")

		return sets

# lvl = 78
# nature = Nature.ADAMANT

# stats = [
# 	Stat(StatType.HP,    base=108, iv=24, lvl=lvl, ev=74),
# 	Stat(StatType.ATK,   base=130, iv=12, lvl=lvl, ev=190, mult=1.1),
# 	Stat(StatType.DEF,   base=95,  iv=30, lvl=lvl, ev=91),
# 	Stat(StatType.SPATK, base=80,  iv=16, lvl=lvl, ev=48,  mult=0.9),
# 	Stat(StatType.SPDEF, base=85,  iv=23, lvl=lvl, ev=84),
# 	Stat(StatType.SPEED, base=102, iv=5,  lvl=lvl, ev=23)
# ]
# for stat in stats:
# 	print(f"{stat._type.name}: {stat.getVal(lvl)}")
#
# stats = [
# 	Stat(StatType.HP,    base=108, val=289, lvl=lvl, ev=74),              # 24
# 	Stat(StatType.ATK,   base=130, val=278, lvl=lvl, ev=190, mult=1.1),   # 12
# 	Stat(StatType.DEF,   base=95,  val=193, lvl=lvl, ev=91),              # 30
# 	Stat(StatType.SPATK, base=80,  val=135, lvl=lvl, ev=48,  mult=0.9),   # 16
# 	Stat(StatType.SPDEF, base=85,  val=171, lvl=lvl, ev=84),              # 23
# 	Stat(StatType.SPEED, base=102, val=171, lvl=lvl, ev=23)               # 5
# ]
#
# for stat in stats:
# 	print(f"{stat._type.name}: {stat.getIVRange()}")


r = Representative(
	spec=Pokemon.MAGIKARP,
	lvl=25,
	nature=Nature.ADAMANT,
	characteristic=Characteristic.LIKES_TO_TRASH_ABOUT,
	stats={
		StatType.HP: {"value": 51},
		StatType.ATK: {"value": 17},
		StatType.DEF: {"value": 39},
		StatType.SPATK: {"value": 15},
		StatType.SPDEF: {"value": 18},
		StatType.SPEED: {"value": 51}
	}
)

ivSets = r.getIVSets()

for statType, ivSet in ivSets.items():
	print(f"{statType.name}: {ivSet}")

