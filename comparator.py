from collections.abc import Collection
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, TypeVar, Callable, Self

from characteristic import Characteristic
from nature import Nature
from pkmn_stat import IVRanges, EVs, StatData, StatsData, GenStats, GenStatsNormalized, Stat
from pkmn_stat_type import StatType, GenStatType
from pokemon import Species, Pokemon, Sample, Species_T
from utils import SEnum, enum, enum_const_dict, NumRange, FloatRange, IntRange, IntOrRange_T, pretty_print


# TODO: in all possible places handle IV, EV and base values of stats are in
#       allowed ranges, including sum of EV <= 510.


GenComparison_T = tuple[dict[int, GenStats], None]
GenComparisonNormalized_T = tuple[dict[int, GenStatsNormalized], GenStats]
Comparison_T = GenComparison_T | GenComparisonNormalized_T

CompSimpleKey_T = int | Fraction | float
_Strategy_T = Callable[
	[GenStats | GenStatsNormalized],
	CompSimpleKey_T | tuple[CompSimpleKey_T, ...]
]
Strategy_T = Callable[[dict[Sample, GenStats | GenStatsNormalized]], _Strategy_T]


@dataclass(slots=True)
class SampleSpecificData:
	iv_ranges: IVRanges
	nature: Nature
	evs: EVs = None
	characteristic: Characteristic = None
	name: str = None


class _EvenEVs:
	pass


EVEN_EVS = _EvenEVs()


class PokemonComparator:
	def __init__(
		self,
		*samples: Sample,
		ref_sample: Sample | int = None
	):
		self._samples_list = [*samples]
		# Save initial samples order for fast retrieval.
		self._samples = {s: i for i, s in enumerate(self._samples_list)}

		if isinstance(ref_sample, int):
			# Use one of input samples as reference sample.
			if ref_sample < 0:
				# Handle from-the-end indexes.
				ref_sample += len(self._samples)

			if not (0 <= ref_sample < len(self._samples)):
				raise IndexError("Reference sample index is out of range")

			for s, i in self._samples.items():
				if i == ref_sample:
					self._ref_sample = deepcopy(s)
			self._ref_sample: Sample

		else:
			self._ref_sample = ref_sample

	@staticmethod
	def _sample_evs(common_evs: EVs, sample_data: SampleSpecificData, stat_type: StatType) -> IntOrRange_T | None:
		return sample_data.evs[stat_type]

	@staticmethod
	def _even_evs(common_evs: EVs, sample_data: SampleSpecificData, stat_type: StatType) -> int:
		return Stat.EV_RANGE.max // len(StatType)

	@staticmethod
	def _common_evs(common_evs: EVs, sample_data: SampleSpecificData, stat_type: StatType) -> int:
		return common_evs[stat_type]

	@classmethod
	def from_same_species(
		cls,
		spec: Species_T,
		*samples_data: SampleSpecificData,
		lvl: int = None,
		evs: EVs | _EvenEVs | None = EVEN_EVS,
		ref_sample_data: SampleSpecificData | int = None
	) -> Self:
		if evs is None:
			evs_getter = cls._sample_evs
		elif evs is EVEN_EVS:
			evs_getter = cls._even_evs
		else:
			evs_getter = cls._common_evs

		samples = tuple(
			Sample(
				spec,
				sample_data.nature,
				sample_data.characteristic,
				lvl,
				StatsData({
					stat_type: StatData(
						iv=sample_data.iv_ranges[stat_type],
						ev=evs_getter(evs, sample_data, stat_type)
					)
					for stat_type in StatType
				}),
				sample_data.name
			)
			for sample_data in samples_data
		)

		if isinstance(ref_sample_data, SampleSpecificData):
			ref_sample = Sample(
				spec,
				ref_sample_data.nature,
				ref_sample_data.characteristic,
				lvl,
				StatsData({
					stat_type: StatData(
						iv=ref_sample_data.iv_ranges[stat_type],
						ev=evs_getter(evs, ref_sample_data, stat_type)
					)
					for stat_type in StatType
				}),
				ref_sample_data.name
			)
		else:
			# int | None
			ref_sample = ref_sample_data

		return cls(*samples, ref_sample=ref_sample)

	@staticmethod
	def normalized(stats: GenStats, ref_stats: GenStats) -> GenStatsNormalized:
		return GenStatsNormalized({
			stat_type: stat_value / ref_stats[stat_type]
			for stat_type, stat_value in stats.items()
		})

	class RangeStrategy(SEnum):
		MIN = enum.auto()
		MID = enum.auto()
		MAX = enum.auto()
		DEFAULT = MID

	_RANGE_STRATEGY_LAMBDAS = {
		RangeStrategy.MIN: lambda val_range: NumRange.get_min(val_range),
		RangeStrategy.MID: lambda val_range: NumRange.get_mid(val_range),
		RangeStrategy.MAX: lambda val_range: NumRange.get_max(val_range)
	}

	@classmethod
	def simple_strategy(
		cls,
		*stat_types: GenStatType,
		range_strategy: RangeStrategy = RangeStrategy.DEFAULT
	) -> Strategy_T:
		"""Returns key for sorting: tuple of stat values in given order."""
		if not stat_types:
			raise ValueError("At least one stat type is required")

		def _simple_strategy(samples_stats: dict[Sample, GenStats | GenStatsNormalized]) -> _Strategy_T:
			return lambda sample: tuple(
				cls._RANGE_STRATEGY_LAMBDAS[range_strategy](samples_stats[sample][stat_type])
				for stat_type in stat_types
			)

		return _simple_strategy

	def get_comparison(self, strategy: Strategy_T, lvl: int = None) -> Comparison_T:
		samples_stats = {sample: sample.getGenStats(lvl) for sample in self._samples}

		ref_stats = None
		if self._ref_sample is not None:
			ref_stats = self._ref_sample.getGenStats(lvl)
			for sample, stats in samples_stats.items():
				samples_stats[sample] = self.normalized(stats, ref_stats)

		final_order = sorted(samples_stats, key=strategy(samples_stats), reverse=True)

		result = {
			self._samples[sample]: samples_stats[sample]
			for sample in final_order
		}

		return result, ref_stats

	def pretty_print_results(self, sorted_stats: dict[int, GenStats], ref_stats: GenStats = None) -> None:
		ROW_SEP = '-'
		COL_SEP = ' | '
		header_len = max(len(nature.name) for nature in Nature) + len(" @ 99")
		col_len = len(f'{FloatRange(0.001, 0.002):.3f}') + 2

		header = 'Stat type'.rjust(header_len)
		print(f'{header}{COL_SEP}', end='')
		print(COL_SEP.join(
			stat_type.name.rjust(col_len)
			for stat_type in GenStatType
		))

		row_len = header_len + (len(COL_SEP) + col_len) * len(GenStatType)
		print(ROW_SEP * row_len)

		for initial_pos, stats in sorted_stats.items():
			sample = self._samples_list[initial_pos]
			header = f'{sample.nature.name} @ {initial_pos}'.rjust(header_len)
			print(f'{header}{COL_SEP}', end='')
			print(COL_SEP.join(
				f'{stat_val:.3f}'.rjust(col_len)
				for stat_val in stats.values()
			))

		if ref_stats is not None:
			print(" REFERENCE ".center(row_len, ROW_SEP))
			sample = self._ref_sample
			sample_nature: str | None = sample.nature
			if sample_nature is None:
				sample_nature_str = str(None)
			else:
				sample_nature: Nature
				sample_nature_str = sample_nature.name
			print(f'{sample_nature_str.rjust(header_len)}{COL_SEP}', end='')
			print(COL_SEP.join(
				f'{stat_val}'.rjust(col_len)
				for stat_val in ref_stats.values()
			))


def main():
	# lvl = 30
	#
	# rGentle = Sample(
	# 	spec=Pokemon.AGGRON,
	# 	nature=Nature.GENTLE,
	# 	lvl=lvl,
	# 	stats={
	# 		StatType.HP: {"iv": IntRange(20, 21), "ev": 85},
	# 		StatType.ATK: {"iv": 20, "ev": 85},
	# 		StatType.DEF: {"iv": IntRange(7, 11), "ev": 85},
	# 		StatType.SPATK: {"iv": IntRange(15, 19), "ev": 85},
	# 		StatType.SPDEF: {"iv": IntRange(15, 18), "ev": 85},
	# 		StatType.SPEED: {"iv": 0, "ev": 85},
	# 	}
	# )
	# genStats = rGentle.getGenStats()
	# pretty_print(genStats)
	# print()
	#
	# print(PokemonComparator.simple_strategy(
	# 	GenStatType.SPDUR,
	# 	GenStatType.ATK,
	# 	GenStatType.DUR,
	# 	GenStatType.SPEED,
	# 	range_strategy=PokemonComparator.RangeStrategy.MIN
	# )(genStats))

	comp = PokemonComparator.from_same_species(
		Pokemon.AGGRON,
		SampleSpecificData(iv_ranges=IVRanges({
			StatType.HP: IntRange(20, 23),
			StatType.ATK: 23,
			StatType.DEF: IntRange(25, 26),
			StatType.SPATK: IntRange(20, 25),
			StatType.SPDEF: IntRange(15, 19),
			StatType.SPEED: 14,
		}), nature=Nature.QUIRKY),
		SampleSpecificData(iv_ranges=IVRanges({
			StatType.HP: IntRange(14, 17),
			StatType.ATK: IntRange(14, 16),
			StatType.DEF: 13,
			StatType.SPATK: IntRange(3, 6),
			StatType.SPDEF: IntRange(27, 31),
			StatType.SPEED: IntRange(3, 6),
		}), nature=Nature.HARDY),
		SampleSpecificData(iv_ranges=IVRanges({
			StatType.HP: IntRange(7, 9),
			StatType.ATK: 4,
			StatType.DEF: 23,
			StatType.SPATK: 14,
			StatType.SPDEF: IntRange(27, 31),
			StatType.SPEED: 9,
		}), nature=Nature.ADAMANT),
		SampleSpecificData(iv_ranges=IVRanges({
			StatType.HP: 24,
			StatType.ATK: 30,
			StatType.DEF: 15,
			StatType.SPATK: IntRange(15, 19),
			StatType.SPDEF: IntRange(20, 23),
			StatType.SPEED: 15,
		}), nature=Nature.LONELY),
		SampleSpecificData(iv_ranges=IVRanges({
			StatType.HP: 25,
			StatType.ATK: IntRange(10, 11),
			StatType.DEF: 10,
			StatType.SPATK: 30,
			StatType.SPDEF: IntRange(27, 29),
			StatType.SPEED: IntRange(21, 23),
		}), nature=Nature.RELAXED),
		SampleSpecificData(iv_ranges=IVRanges({
			StatType.HP: IntRange(20, 21),
			StatType.ATK: 20,
			StatType.DEF: IntRange(7, 11),
			StatType.SPATK: IntRange(15, 19),
			StatType.SPDEF: IntRange(15, 18),
			StatType.SPEED: 0,
		}), nature=Nature.GENTLE),
		SampleSpecificData(iv_ranges=IVRanges({
			StatType.HP: IntRange(7, 8),
			StatType.ATK: 14,
			StatType.DEF: IntRange(14, 15),
			StatType.SPATK: IntRange(10, 13),
			StatType.SPDEF: IntRange(27, 29),
			StatType.SPEED: IntRange(20, 21),
		}), nature=Nature.CALM),
		SampleSpecificData(iv_ranges=IVRanges({
			StatType.HP: IntRange(14, 15),
			StatType.ATK: 3,
			StatType.DEF: IntRange(0, 4),
			StatType.SPATK: 3,
			StatType.SPDEF: IntRange(20, 23),
			StatType.SPEED: 27,
		}), nature=Nature.JOLLY),
		SampleSpecificData(iv_ranges=IVRanges({
			StatType.HP: IntRange(29, 31),
			StatType.ATK: IntRange(2, 3),
			StatType.DEF: 14,
			StatType.SPATK: IntRange(20, 25),
			StatType.SPDEF: IntRange(15, 19),
			StatType.SPEED: 22,
		}), nature=Nature.HASTY),
		evs=EVs({
			StatType.HP: 252,
			StatType.ATK: 0,
			StatType.DEF: 6,
			StatType.SPATK: 0,
			StatType.SPDEF: 252,
			StatType.SPEED: 0
		}),
		ref_sample_data=4  # RELAXED
	)

	comp_result, ref_stats = comp.get_comparison(
		PokemonComparator.simple_strategy(
			GenStatType.SPDUR,
			GenStatType.ATK,
			GenStatType.DUR,
			GenStatType.SPEED),
		lvl=70
	)
	comp.pretty_print_results(comp_result, ref_stats)


if __name__ == "__main__":
	main()
