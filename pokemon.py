from __future__ import annotations
from enum import Enum
from typing import Dict, Union

import voluptuous as vlps

from catch import CATCH_RATE_RANGE
from characteristic import Characteristic, CharacteristicData
from nature import Nature
from pkmn_stat import Stat, StatType, BaseStats, StatData, StatsData, LVL_RANGE
from utils import pretty_print


class Species:
	def __init__(
		self,
		base_stats: Union[BaseStats, Dict[StatType, int]],
		name: str = None,
		catch_rate: int = None
	):
		if not isinstance(base_stats, BaseStats):
			# Auto validation.
			base_stats = BaseStats(base_stats)
		self._base_stats = base_stats
		self._stats = None  # placeholder for child-class

		self._name = vlps.Schema(str)(name)
		self._catchRate = vlps.Schema(vlps.All(int, vlps.Range(*CATCH_RATE_RANGE)))(catch_rate)


class Representative(Species):
	def __init__(
		self,
		spec: Union[Species, Pokemon],
		nature: Nature = None,
		characteristic: Characteristic = None,
		lvl: int = None,
		# Second variant for `stats` argument is:
		# {
		#     StatType.HP: 100,  # `value` argument
		#     StatType.ATK: {"value": 70, "ev": 252},
		#     ...
		# }
		stats: Union[StatsData, Dict[StatType, Union[int, Dict[str, int]]]] = None
	):
		if nature is None:
			raise NotImplementedError

		spec = vlps.Schema(vlps.Any(Species, Pokemon))(spec)
		if isinstance(spec, Pokemon):
			spec = spec.value
		spec: Species
		super().__init__(spec._base_stats, spec._name, spec._catchRate)

		self._nature = vlps.Schema(Nature)(nature)
		self._characteristic = vlps.Schema(Characteristic)(characteristic)
		self._lvl = vlps.Schema(vlps.All(int, vlps.Range(*LVL_RANGE)))(lvl)

		if stats is None:
			stats = StatsData({
				stat_type: StatData()
				for stat_type in StatType
			})
		elif not isinstance(stats, StatsData):
			# Auto validation.
			stats = StatsData({
				stat_type: StatData(stat_data) if isinstance(stat_data, int) else StatData(**stat_data)
				for stat_type, stat_data in stats.items()
			})
		stats: StatsData

		self._stats = {}
		for stat_type in StatType:
			base_stat = spec._base_stats[stat_type]
			stat = stats[stat_type]

			if stat_type == StatType.HP:
				nature_mult = None
			elif stat_type == nature.increased and not nature.is_simple():
				nature_mult = Stat.INCREASED_MULT
			elif stat_type == nature.decreased and not nature.is_simple():
				nature_mult = Stat.DECREASED_MULT
			else:
				nature_mult = Stat.DEFAULT_MULT

			self._stats[stat_type] = Stat(
				stat_type,
				base_stat,
				lvl,
				stat.value,
				stat.iv,
				stat.ev,
				nature_mult
			)

	def get_iv_sets(self):
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
			highest_stat, rem = self._characteristic.highest_stat, self._characteristic.rem
			sets[highest_stat] = {val for val in sets[highest_stat] if val % CharacteristicData.MOD == rem}
			if not sets[highest_stat]:
				raise ValueError(f"This {self._name} has impossible input values")

			highest_stat_max_val = max(sets[highest_stat])
			for type_, set_ in sets.items():
				if type_ != highest_stat:
					sets[type_] = {val for val in sets[type_] if val <= highest_stat_max_val}
					if not sets[type_]:
						raise ValueError(f"This {self._name} has impossible input values")

		return sets


class Pokemon(Enum):
	MAGIKARP = Species(name="Magikarp", catch_rate=255, base_stats={
		StatType.HP: 20,
		StatType.ATK: 10,
		StatType.DEF: 55,
		StatType.SPATK: 15,
		StatType.SPDEF: 20,
		StatType.SPEED: 80
	})

	RAYQUAZA = Species(name="Rayquaza", catch_rate=45, base_stats={
		StatType.HP: 105,
		StatType.ATK: 150,
		StatType.DEF: 90,
		StatType.SPATK: 150,
		StatType.SPDEF: 90,
		StatType.SPEED: 95
	})

	MEGA_RAYQUAZA = Species(name="Mega Rayquaza", catch_rate=45, base_stats={
		StatType.HP: 105,
		StatType.ATK: 180,
		StatType.DEF: 100,
		StatType.SPATK: 180,
		StatType.SPDEF: 100,
		StatType.SPEED: 115
	})


def main():
	pretty_print(Pokemon)


if __name__ == "__main__":
	main()

