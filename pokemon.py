from __future__ import annotations
from collections.abc import Collection
from enum import Enum
from typing import Dict, Union, Set

import voluptuous as vlps

from catch import CATCH_RATE_RANGE
from characteristic import Characteristic, CharacteristicData
from nature import Nature
from pkmn_stat import Stat, BaseStats, GenStats, StatData, StatsData, LVL_RANGE
from pkmn_stat_type import StatType, GenStatType
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


NatureIVSets_T = Dict[StatType, Set[int]]
IVSets_T = Dict[Nature, NatureIVSets_T]


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
		spec = vlps.Schema(vlps.Any(Species, Pokemon))(spec)
		if isinstance(spec, Pokemon):
			spec = spec.value
		spec: Species
		super().__init__(spec._base_stats, spec._name, spec._catchRate)

		self._nature = vlps.Schema(vlps.Maybe(Nature))(nature)
		self._characteristic = vlps.Schema(vlps.Maybe(Characteristic))(characteristic)
		self._lvl = vlps.Schema(vlps.Maybe(vlps.All(int, vlps.Range(*LVL_RANGE))))(lvl)

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

			if stat_type == StatType.HP or nature is None:
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

	def getGenStats(self, lvl: int = None) -> GenStats:
		statValues = {
			statType: stat.get_val(lvl)
			for statType, stat in self._stats.items()
		}
		return GenStats({
			GenStatType.ATTACK: statValues[StatType.ATK],
			GenStatType.DURABILITY: statValues[StatType.HP] * statValues[StatType.DEF],
			GenStatType.SPATTACK: statValues[StatType.SPATK],
			GenStatType.SPDURABILITY: statValues[StatType.HP] * statValues[StatType.SPDEF],
			GenStatType.SPEED: statValues[StatType.SPEED]
		})

	@staticmethod
	def _characteristic_filter(
		iv_sets: NatureIVSets_T,
		characteristic: Characteristic
	) -> NatureIVSets_T:
		highest_stat, rem = characteristic.highest_stat, characteristic.rem
		iv_sets[highest_stat] = {val for val in iv_sets[highest_stat] if val % CharacteristicData.MOD == rem}
		if not iv_sets[highest_stat]:
			raise ValueError("Stats have impossible values")

		highest_stat_max_val = max(iv_sets[highest_stat])
		for type_, set_ in iv_sets.items():
			if type_ != highest_stat:
				iv_sets[type_] = {val for val in iv_sets[type_] if val <= highest_stat_max_val}
				if not iv_sets[type_]:
					raise ValueError("Stats have impossible values")

		return iv_sets

	@classmethod
	def _get_iv_sets_with_nature(
		cls,
		stats: Dict[StatType, Stat],  # nature multiplier must be set for all stats
		characteristic: Characteristic = None
	) -> NatureIVSets_T:
		iv_ranges = {
			stat_type: stat.get_iv_range()
			for stat_type, stat in stats.items()
		}

		iv_sets = {
			type_: set(range(range_[0], range_[1] + 1))
			for type_, range_ in iv_ranges.items()
		}

		if characteristic is not None:
			iv_sets = cls._characteristic_filter(iv_sets, characteristic)

		return iv_sets

	def get_iv_sets(self) -> IVSets_T:
		if self._lvl is None:
			raise ValueError("Lvl must be specified")

		if self._nature is not None:
			return {
				self._nature: self._get_iv_sets_with_nature(self._stats, self._characteristic)
			}

		# #####################################################################
		# Nature is not defined                                               #
		# #####################################################################

		# For each stat_type find possible iv_sets for different nature mults.
		pre_iv_sets = {}
		for stat_type, stat in self._stats.items():
			mult_iv_sets = {}
			if stat_type == StatType.HP:
				iv_range = stat.get_iv_range()
				mult_iv_sets[None] = set(range(iv_range[0], iv_range[1] + 1))
			else:
				for mult in Stat.POSSIBLE_NATURE_MULTS:
					try:
						iv_range = stat.get_iv_range(mult=mult)
					except ValueError:
						continue
					mult_iv_sets[mult] = set(range(iv_range[0], iv_range[1] + 1))

				if not mult_iv_sets:
					raise ValueError(f"Calculated {stat_type.name} IVs are impossible")

			pre_iv_sets[stat_type] = mult_iv_sets

		# Define possible natures.
		iv_sets = {}
		for nature in Nature:
			# All simple natures are equivalent if characteristic is not defined.
			if nature.is_simple() and self._characteristic is None and nature != Nature.DEFAULT:
				continue

			try:
				nature_iv_sets = {
					stat_type: mult_iv_sets[Stat.get_mult(stat_type, nature)]
					for stat_type, mult_iv_sets in pre_iv_sets.items()
				}
			except KeyError:
				continue

			if self._characteristic is not None:
				try:
					nature_iv_sets = self._characteristic_filter(nature_iv_sets, self._characteristic)
				except ValueError:
					continue

			iv_sets[nature] = nature_iv_sets

		if not iv_sets:
			raise ValueError("Stats have impossible values")

		return iv_sets


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

	TOTODILE = Species(name="Totodile", catch_rate=45, base_stats={
		StatType.HP: 50,
		StatType.ATK: 65,
		StatType.DEF: 64,
		StatType.SPATK: 44,
		StatType.SPDEF: 48,
		StatType.SPEED: 43
	})

	AGGRON = Species(name="Aggron", catch_rate=45, base_stats={
		StatType.HP: 70,
		StatType.ATK: 110,
		StatType.DEF: 180,
		StatType.SPATK: 60,
		StatType.SPDEF: 60,
		StatType.SPEED: 50
	})


def main():
	lvl = 70

	rGentle = Representative(
		spec=Pokemon.AGGRON,
		nature=Nature.GENTLE,
		lvl=lvl,
		stats={
			StatType.HP: {"iv": 20},
			StatType.ATK: {"iv": 20},
			StatType.DEF: {"iv": 7},
			StatType.SPATK: {"iv": 15},
			StatType.SPDEF: {"iv": 20},
			StatType.SPEED: {"iv": 0},
		}
	)

	for st, sv in rGentle.getGenStats().items():
		print(f"{st}: {sv}")


if __name__ == "__main__":
	main()

