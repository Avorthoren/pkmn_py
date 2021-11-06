from enum import Enum

from pkmn_stat import Stat, StatType


class Species:
	def __init__(self, name, catchRate, baseStats):
		self._name = name
		self._catchRate = catchRate
		self._stats = {
			type_: Stat(type_, base=baseStats[type_])
			for type_ in StatType
		}


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
			type_: self._stats[type_].get_iv_range()
			for type_ in StatType
		}

		sets = {
			type_: set(range(range_[0], range_[1] + 1))
			for type_, range_ in ranges.items()
		}

		if self._characteristic is not None:
			highestStat, rem = self._characteristic.value._highest_stat, self._characteristic.value._rem
			sets[highestStat] = {val for val in sets[highestStat] if val % 5 == rem}
			if not sets[highestStat]:
				raise ValueError(f"This {self._name} has impossible input values")

			for type_, set_ in sets.items():
				if type_ != highestStat:
					sets[type_] = {val for val in sets[type_] if val <= max(sets[highestStat])}
					if not sets[type_]:
						raise ValueError(f"This {self._name} has impossible input values")

		return sets


class Pokemon(Enum):
	MAGIKARP = Species("Magikarp", catchRate=255, baseStats={
		StatType.HP: 20,
		StatType.ATK: 10,
		StatType.DEF: 55,
		StatType.SPATK: 15,
		StatType.SPDEF: 20,
		StatType.SPEED: 80
	})

	RAYQUAZA = Species("Rayquaza", catchRate=45, baseStats={
		StatType.HP: 105,
		StatType.ATK: 150,
		StatType.DEF: 90,
		StatType.SPATK: 150,
		StatType.SPDEF: 90,
		StatType.SPEED: 95
	})

	MEGA_RAYQUAZA = Species("Mega Rayquaza", catchRate=45, baseStats={
		StatType.HP: 105,
		StatType.ATK: 180,
		StatType.DEF: 100,
		StatType.SPATK: 180,
		StatType.SPDEF: 100,
		StatType.SPEED: 115
	})

