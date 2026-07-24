import math
from collections.abc import Collection
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, TypeVar, Callable
from typing_extensions import Self

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


class _NoEVs:
	pass


NO_EVS = _NoEVs()


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
	def _sample_evs(_, sample_data: SampleSpecificData, stat_type: StatType) -> IntOrRange_T | None:
		return sample_data.evs[stat_type]

	@staticmethod
	def _no_evs(*_, **__) -> int:
		return 0

	@staticmethod
	def _even_evs(*_, **__) -> int:
		return Stat.EV_RANGE.max // len(StatType)

	@staticmethod
	def _common_evs(common_evs: EVs, _, stat_type: StatType) -> int:
		return common_evs[stat_type]

	@classmethod
	def from_same_species(
		cls,
		spec: Species_T,
		*samples_data: SampleSpecificData,
		lvl: int = None,
		evs: EVs | _NoEVs | _EvenEVs | None = NO_EVS,
		ref_sample_data: SampleSpecificData | int = None
	) -> Self:
		if evs is None:
			evs_getter = cls._sample_evs
		elif evs is NO_EVS:
			evs_getter = cls._no_evs
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
		samples_stats = {sample: sample.get_gen_stats_values(lvl) for sample in self._samples}

		ref_stats = None
		if self._ref_sample is not None:
			ref_stats = self._ref_sample.get_gen_stats_values(lvl)
			for sample, stats in samples_stats.items():
				samples_stats[sample] = self.normalized(stats, ref_stats)

		final_order = sorted(samples_stats, key=strategy(samples_stats), reverse=True)

		result = {
			self._samples[sample]: samples_stats[sample]
			for sample in final_order
		}

		return result, ref_stats

	def pretty_print_results(
		self,
		sorted_stats: dict[int, GenStats],
		ref_stats: GenStats = None,
		mid_values: bool = False,
		precision: int = 2  # used when ref_stats is not None
	) -> None:
		if not sorted_stats:
			raise ValueError("sorted_stats should not be empty!")

		# Prepare.
		ROW_SEP = '-'
		COL_SEP = ' | '
		header_len = max(len(nature.name) for nature in Nature) + len(f" @ {len(sorted_stats) - 1}")

		col_lens = {}
		for stat_type in GenStatType:
			col_len = len(stat_type.name)

			if stat_type in (GenStatType.DUR, GenStatType.SPDUR):
				# Max DURABILITY is 390600 (6 digits).
				_val = 100_000  # do not change to 999_999, will be multiplied further.
			else:
				# Max ATK is 669 (3 digits).
				_val = 100  # do not change to 999, will be multiplied further.

			if mid_values:
				col_len = max(len(str(_val)), col_len)
			else:
				col_len = max(len(f'{FloatRange(_val, 2 * _val)}'), col_len)

			if ref_stats is not None:
				_val = 1 + pow(10, -precision)
				if mid_values:
					col_len = max(len(str(_val)), col_len)
				else:
					col_len = max(len(f'{FloatRange(_val, 2 * _val):.{precision}f}'), col_len)

			col_lens[stat_type] = col_len

		fmt = '.0f' if ref_stats is None else f'.{precision}f'

		# Print.
		header = 'Stat type'.rjust(header_len)
		print(f'{header}{COL_SEP}', end='')
		print(COL_SEP.join(
			stat_type.name.rjust(col_lens[stat_type])
			for stat_type in GenStatType
		))

		row_len = header_len + len(COL_SEP) * len(GenStatType) + sum(col_lens.values())
		print(ROW_SEP * row_len)

		for initial_pos, stats in sorted_stats.items():
			sample = self._samples_list[initial_pos]
			header = f'{sample.nature.name} @ {initial_pos}'.rjust(header_len)
			print(f'{header}{COL_SEP}', end='')
			print(COL_SEP.join(
				f'{IntRange.get_mid(stat_val) if mid_values else stat_val:{fmt}}'.rjust(col_lens[stat_type])
				for stat_type, stat_val in stats.items()
			))  # , sum(IntRange.get_mid(stat_val) for stat_val in stats.values()))

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
				f'{IntRange.get_mid(stat_val) if mid_values else stat_val:.0f}'.rjust(col_lens[stat_type])
				for stat_type, stat_val in ref_stats.items()
			))


def dur_atk_strategy(samples_stats: dict[Sample, GenStatsNormalized]) -> _Strategy_T:
	return lambda sample: (
		NumRange.get_mid(samples_stats[sample][GenStatType.DUR])
		+ NumRange.get_mid(samples_stats[sample][GenStatType.SPDUR]),
		NumRange.get_mid(samples_stats[sample][GenStatType.ATK])
		+ NumRange.get_mid(samples_stats[sample][GenStatType.SPATK]),
	)


def geomdur_atk_spd_strategy(samples_stats: dict[Sample, GenStatsNormalized]) -> _Strategy_T:
	return lambda sample: (
		math.sqrt(
			NumRange.get_mid(samples_stats[sample][GenStatType.DUR])
			* NumRange.get_mid(samples_stats[sample][GenStatType.SPDUR])
		),
		NumRange.get_mid(samples_stats[sample][GenStatType.ATK]),
		NumRange.get_mid(samples_stats[sample][GenStatType.SPEED]),
	)


def dur_allatkspd_strategy(samples_stats: dict[Sample, GenStatsNormalized]) -> _Strategy_T:
	return lambda sample: (
		NumRange.get_mid(samples_stats[sample][GenStatType.DUR])
		+ NumRange.get_mid(samples_stats[sample][GenStatType.SPDUR]),
		NumRange.get_mid(samples_stats[sample][GenStatType.ATK])
		+ NumRange.get_mid(samples_stats[sample][GenStatType.SPATK])
		+ NumRange.get_mid(samples_stats[sample][GenStatType.SPEED])
	)


def dur_spatkspd_strategy(samples_stats: dict[Sample, GenStatsNormalized]) -> _Strategy_T:
	return lambda sample: (
		NumRange.get_mid(samples_stats[sample][GenStatType.DUR])
		+ NumRange.get_mid(samples_stats[sample][GenStatType.SPDUR]),
		NumRange.get_mid(samples_stats[sample][GenStatType.SPATK])
		+ NumRange.get_mid(samples_stats[sample][GenStatType.SPEED])
	)


def simple_sum(samples_stats: dict[Sample, GenStatsNormalized]) -> _Strategy_T:
	return lambda sample: sum(
		NumRange.get_mid(samples_stats[sample][stat_type])
		for stat_type in GenStatType
	)


def allatkspd_dur_strategy(samples_stats: dict[Sample, GenStatsNormalized]) -> _Strategy_T:
	return lambda sample: (
		NumRange.get_mid(samples_stats[sample][GenStatType.ATK])
		+ NumRange.get_mid(samples_stats[sample][GenStatType.SPATK])
		+ NumRange.get_mid(samples_stats[sample][GenStatType.SPEED]),
		NumRange.get_mid(samples_stats[sample][GenStatType.DUR])
		+ NumRange.get_mid(samples_stats[sample][GenStatType.SPDUR])
	)


def spatkspd_dur_atk_strategy(samples_stats: dict[Sample, GenStatsNormalized]) -> _Strategy_T:
	return lambda sample: (
		NumRange.get_mid(samples_stats[sample][GenStatType.SPATK])
		+ NumRange.get_mid(samples_stats[sample][GenStatType.SPEED]),
		NumRange.get_mid(samples_stats[sample][GenStatType.DUR])
		+ NumRange.get_mid(samples_stats[sample][GenStatType.SPDUR]),
		NumRange.get_mid(samples_stats[sample][GenStatType.ATK])
	)


def allexceptdur_dur(samples_stats: dict[Sample, GenStatsNormalized]) -> _Strategy_T:
	return lambda sample: (
		NumRange.get_mid(samples_stats[sample][GenStatType.ATK])
		+ NumRange.get_mid(samples_stats[sample][GenStatType.SPATK])
		+ NumRange.get_mid(samples_stats[sample][GenStatType.SPEED])
		+ NumRange.get_mid(samples_stats[sample][GenStatType.SPDUR]),
		NumRange.get_mid(samples_stats[sample][GenStatType.DUR])
	)


def main():
	comp = PokemonComparator.from_same_species(
		Pokemon.BRELOOM,

		SampleSpecificData(iv_ranges=IVRanges({
			StatType.HP: IntRange(30, 31),
			StatType.ATK: IntRange(6, 7),
			StatType.DEF: IntRange(31, 31),
			StatType.SPATK: IntRange(2, 2),
			StatType.SPDEF: IntRange(30, 31),
			StatType.SPEED: IntRange(13, 14)
		}), nature=Nature.ADAMANT),
		SampleSpecificData(iv_ranges=IVRanges({
			StatType.HP: IntRange(28, 29),
			StatType.ATK: IntRange(31, 31),
			StatType.DEF: IntRange(15, 16),
			StatType.SPATK: IntRange(16, 19),
			StatType.SPDEF: IntRange(20, 20),
			StatType.SPEED: IntRange(11, 11)
		}), nature=Nature.ADAMANT),
		SampleSpecificData(iv_ranges=IVRanges({
			StatType.HP: IntRange(25, 25),
			StatType.ATK: IntRange(30, 31),
			StatType.DEF: IntRange(3, 3),
			StatType.SPATK: IntRange(30, 31),
			StatType.SPDEF: IntRange(31, 31),
			StatType.SPEED: IntRange(30, 31)
		}), nature=Nature.ADAMANT),
		SampleSpecificData(iv_ranges=IVRanges({
			StatType.HP: IntRange(31, 31),
			StatType.ATK: IntRange(7, 7),
			StatType.DEF: IntRange(28, 29),
			StatType.SPATK: IntRange(16, 19),
			StatType.SPDEF: IntRange(20, 20),
			StatType.SPEED: IntRange(3, 4)
		}), nature=Nature.ADAMANT),
		SampleSpecificData(iv_ranges=IVRanges({
			StatType.HP: IntRange(19, 19),
			StatType.ATK: IntRange(31, 31),
			StatType.DEF: IntRange(30, 31),
			StatType.SPATK: IntRange(3, 4),
			StatType.SPDEF: IntRange(23, 23),
			StatType.SPEED: IntRange(17, 20)
		}), nature=Nature.ADAMANT),
		SampleSpecificData(iv_ranges=IVRanges({
			StatType.HP: IntRange(23, 24),
			StatType.ATK: IntRange(26, 28),
			StatType.DEF: IntRange(9, 9),
			StatType.SPATK: IntRange(31, 31),
			StatType.SPDEF: IntRange(24, 24),
			StatType.SPEED: IntRange(14, 14)
		}), nature=Nature.ADAMANT),

		ref_sample_data=0
		# ref_sample_data=SampleSpecificData(
		# 	iv_ranges=IVRanges.max(),
		# 	nature=Nature.BOLD
		# ),
	)

	comp_result, ref_stats = comp.get_comparison(
		# PokemonComparator.simple_strategy(
		# 	GenStatType.SPEED,
		# 	GenStatType.ATK,
		# 	GenStatType.DUR,
		# 	GenStatType.SPDUR
		# ),
		# allexceptdur_dur,
		geomdur_atk_spd_strategy,
		lvl=80
	)
	comp.pretty_print_results(
		comp_result,
		ref_stats,
		mid_values=True,
		precision=2
	)


if __name__ == "__main__":
	main()
