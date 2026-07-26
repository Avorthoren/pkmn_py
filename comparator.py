import math
from collections.abc import Collection
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable, TypeVar, Callable, Optional
from typing_extensions import Self

from characteristic import Characteristic
import iv_calc
import iv_calc_ods
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
	nickname: str = None


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
		ref_sample: Optional[Sample | int] = None
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
				sample_data.nickname
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
				ref_sample_data.nickname
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
		ref_stats: Optional[GenStats] = None,
		mid_values: bool = True,
		precision: int = 2  # used when ref_stats is not None
	) -> None:
		if not sorted_stats:
			raise ValueError("sorted_stats should not be empty!")

		# Prepare.
		ROW_SEP = '-'
		COL_SEP = ' | '
		top_header = 'Stat type'
		header_len = max(
			max(
				len(sample.nature.name if sample.nickname is None else sample.nickname)
				for sample in self._samples_list
			) + len(f" @ {len(sorted_stats) - 1}"),
			len(top_header)
		)
		index_len = len(str(len(sorted_stats) - 1))

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
		header = top_header.rjust(header_len)
		print(f'{header}{COL_SEP}', end='')
		print(COL_SEP.join(
			stat_type.name.rjust(col_lens[stat_type])
			for stat_type in GenStatType
		))

		row_len = header_len + len(COL_SEP) * len(GenStatType) + sum(col_lens.values())
		print(ROW_SEP * row_len)

		for initial_pos, stats in sorted_stats.items():
			sample = self._samples_list[initial_pos]
			label = sample.nature.name if sample.nickname is None else sample.nickname
			header = f'{label} @ {initial_pos:>{index_len}}'.rjust(header_len)
			print(f'{header}{COL_SEP}', end='')
			print(COL_SEP.join(
				f'{IntRange.get_mid(stat_val) if mid_values else stat_val:{fmt}}'.rjust(col_lens[stat_type])
				for stat_type, stat_val in stats.items()
			))  # , sum(IntRange.get_mid(stat_val) for stat_val in stats.values()))

		if ref_stats is not None and self._ref_sample is not None:
			print(" REFERENCE ".center(row_len, ROW_SEP))
			sample: Sample = self._ref_sample
			if sample.nickname is None:
				sample_nature: str | None = sample.nature
				if sample_nature is None:
					label = str(None)
				else:
					sample_nature: Nature
					label = sample_nature.name
			else:
				label = sample.nickname
			print(f'{label.rjust(header_len)}{COL_SEP}', end='')
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


def geomduratkspd_strategy(samples_stats: dict[Sample, GenStatsNormalized]) -> _Strategy_T:
	return lambda sample: \
		math.sqrt(
			NumRange.get_mid(samples_stats[sample][GenStatType.DUR])
			* NumRange.get_mid(samples_stats[sample][GenStatType.SPDUR])
		) \
		* NumRange.get_mid(samples_stats[sample][GenStatType.ATK]) \
		* NumRange.get_mid(samples_stats[sample][GenStatType.SPEED])


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


def manual_compare():
	comp = PokemonComparator.from_same_species(
		Pokemon.BRELOOM,

		SampleSpecificData(iv_ranges=IVRanges({
			StatType.HP: IntRange(30, 31),
			StatType.ATK: IntRange(6, 7),
			StatType.DEF: IntRange(31, 31),
			StatType.SPATK: IntRange(2, 2),
			StatType.SPDEF: IntRange(30, 31),
			StatType.SPEED: IntRange(13, 14)
		}), nature=Nature.ADAMANT, nickname="REFERENCE NICKNAME"),
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
		mid_values=False,
		precision=2
	)


def process_compare_ods(
	strategy: Strategy_T,
	lvl: int,
	path: Path | str,
	sheet_name: Optional[str] = None,
	skip: int = 0,
	limit: Optional[int] = None,
	minmax_filter: bool = True,
	important_stat_types: Optional[dict[StatType, bool]] = None,
	ref_sample: Optional[Sample | int] = None,
	spec: Optional[Species_T] = None,
	evs: Optional[dict[StatType, int]] = None,
	mid_values: bool = True,
	precision: int = 2
) -> None:
	"""Print comparison of samples from ODS file.

	Check file format in `iv_calc_ods._parse_ods`.

	============================================================================
	`path`, `sheet_name`, `skip`, `limit`, `important_stat_types`
	and `minmax_filter` passed only to `iv_calc_ods.process_ods_with_filter`.

	If `sheet_name` wasn't specified - all sheets are processed as one.

	`skip` defines how many first sample should be ignored.

	`limit` defines how many samples have to extracted from the file.

	`minmax_filter` defines if samples read from the file should be filtered.
	Check `iv_calc_ods.minmax_filter_samples_iv_sets` for details.

	`important_stat_types` defines stats by which filtered will be executed.
	By default, (`None`) all stats are considered important.

	============================================================================
	`strategy`, `lvl`, `ref_sample`, `spec`, `evs`, `mid_values` and `precision`
	are related to `PokemonComparator`.

	`strategy` defines how samples have to be compared to each other.
	I.e. it calculates sorting key for the sample.

	`lvl` defines on which level should we calculate stats for comparison.

	If `ref_sample` was provided (specific `Sample` or index of sample from
	file), then values in the resulting table will be relative to values
	of that sample. Otherwise, absolute values will be shown.

	If `spec` was provided, all Pokémon from the file will be converted to
	that Species, using calculated IVs.

	If `evs` is `None` - max amount is considered spred equally among
	all `StatType`s. Othwerwise, values from provided dictionary is used,
	with 0 as default value.

	`mid_values` defines is we should print just mid-values in resulting table.

	`precision` used when `ref_stats` is not None for float rounding.
	"""
	if important_stat_types is not None and not minmax_filter:
		raise ValueError("Specifying `important_stat_types` makes sense only if `minmax_filter` is True.")

	samples_iv_sets = iv_calc_ods.get_samples_iv_sets(path, sheet_name, skip, limit)
	if minmax_filter:
		samples_iv_sets, filtered_labels = iv_calc_ods.minmax_filter_samples_iv_sets(
			samples_iv_sets,
			important_stat_types
		)
		if filtered_labels:
			iv_calc_ods.pprint_filtered_labels(filtered_labels)
		print()
	samples_iv_sets = list(samples_iv_sets)

	if evs is None:
		used_evs = {
			stat_type: Sample.MAX_EVS // len(StatType)
			for stat_type in StatType
		}
	else:
		used_evs = {
			stat_type: evs.get(stat_type, 0)
			for stat_type in StatType
		}

	comparator = PokemonComparator(
		*(
			Sample(
				obs_sample["spec"] if spec is None else spec,
				obs_sample["nature"],
				obs_sample["characteristic"],
				nickname=obs_sample["label"],
				stats={
					stat_type: {
						"iv": IntRange(min(calced_iv_set.values), max(calced_iv_set.values)),
						"ev": used_evs[stat_type]
					}
					for stat_type, calced_iv_set in calced_iv_sets.items()
				}
			)
			for obs_sample, calced_iv_sets in samples_iv_sets
		),
		ref_sample=ref_sample
	)

	comp_result, ref_stats = comparator.get_comparison(strategy, lvl)

	comparator.pretty_print_results(comp_result, ref_stats,	mid_values,	precision)
	print()

	print("Top sample IVs:")
	_, top_sample_calced_iv_sets = samples_iv_sets[next(iter(comp_result))]
	iv_calc.pprint_iv_sets(
		top_sample_calced_iv_sets,
		color_mode="mid",
		important_stat_types=important_stat_types,
		print_only_important=False
	)


def main():
	...
	# manual_compare()

	process_compare_ods(
		geomduratkspd_strategy,
		lvl=80,
		path='~/Documents/pkmn/samples/Magikarp.ods',
		sheet_name='Initial',
		skip=0,
		limit=None,
		minmax_filter=True,
		important_stat_types={
			StatType.HP: True,
			StatType.ATK: True,
			StatType.DEF: True,
			StatType.SPDEF: True,
			StatType.SPEED: True
		},
		ref_sample=0,
		spec=Pokemon.GYARADOS,
		# evs={
		# 	StatType.HP: 252,
		# 	StatType.SPDEF: 252,
		# 	StatType.SPEED: 6
		# }
	)


if __name__ == "__main__":
	main()
