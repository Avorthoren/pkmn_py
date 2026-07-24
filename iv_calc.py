import dataclasses
import operator
from collections.abc import Container
from functools import reduce
from typing import Optional, Iterable, TypedDict, Literal

from characteristic import Characteristic
from nature import Nature
from pkmn_stat import StatType, Stat, StatsData, InputStatsData_T, LVL_RANGE
from pokemon import Species_T, Sample, NatureIVSets_T, Pokemon
from utils import colored


class ObsStat(TypedDict):
    lvl: int
    stats: StatsData | InputStatsData_T


@dataclasses.dataclass
class Suggestion:
    # Next level on which IV set will be narrowed.
    update_lvl: Optional[int] = None
    # How much EV should we add so that IV set will be narrowed on the very
    # next level.
    delta_ev: Optional[int] = None


@dataclasses.dataclass
class CalcedIVSet:
    values: set[int] = dataclasses.field(default_factory=lambda: set(Stat.IV_RANGE))
    suggestion: Suggestion = dataclasses.field(default_factory=Suggestion)


type CalcedIVSets_T = dict[StatType, CalcedIVSet]


def get_iv_sets(
    spec: Species_T,
    obs_stats: Iterable[ObsStat],
    nature: Optional[Nature] = None,
    characteristic: Optional[Characteristic] = None,
    label: Optional[str] = None  # not used, just for `ObsSample` matching
) -> CalcedIVSets_T:
    iv_sets: CalcedIVSets_T = {
        stat_type: CalcedIVSet()
        for stat_type in StatType
    }
    # TODO: TEMP, REMOVE. For debug.
    _all_iv_sets = []

    for i, obs_stats_sample in enumerate(obs_stats, start=1):
        sample = Sample(
            spec=spec,
            lvl=obs_stats_sample["lvl"],
            nature=nature,
            characteristic=characteristic,
            stats=obs_stats_sample["stats"],
        )
        # Generally, result will have iv sets for each possible nature, and
        # we have to merge them
        sample_iv_sets = sample.get_iv_sets()
        sample_merged_iv_sets = {
            stat_type: reduce(
                operator.or_,
                (nature_iv_sets[stat_type] for nature_iv_sets in sample_iv_sets.values())
            )
            for stat_type in StatType
        }
        # TODO: TEMP, REMOVE. For debug.
        _all_iv_sets.append({
            "lvl": obs_stats_sample["lvl"],
            "iv": (min(sample_merged_iv_sets[StatType.ATK]), max(sample_merged_iv_sets[StatType.ATK])),
            "ev": obs_stats_sample["stats"][StatType.ATK]["ev"],
            "val": obs_stats_sample["stats"][StatType.ATK]["value"]
        })

        # And finally - intersect with current state of sets:
        _update_iv_sets(i, obs_stats_sample, iv_sets, sample_merged_iv_sets)

        _update_suggestions(sample, iv_sets)

    return iv_sets


def _update_iv_sets(
    i: int,
    obs_stats_sample: ObsStat,
    iv_sets: CalcedIVSets_T,
    sample_merged_iv_sets: NatureIVSets_T
) -> None:
    """Update `iv_sets` given new data: `sample_merged_iv_sets`."""
    for stat_type in StatType:
        stored_values = iv_sets[stat_type].values
        stored_values &= sample_merged_iv_sets[stat_type]
        if not stored_values:
            raise RuntimeError(
                f"{stat_type.name} stats in first {i} blocks are impossible."
                f" Consider double checking stats on LVL {obs_stats_sample['lvl']}"
            )


def _update_suggestions(
    sample: Sample,
    iv_sets: CalcedIVSets_T
) -> None:
    """For each `StatType` in `iv_sets` update `suggestion`:
    1. Next level on which IV set will be narrowed.
    2. How much EV should we add so that IV set will be narrowed on the very
       next level.
    """
    for stat_type, calced_iv_set in iv_sets.items():
        stat = sample.get_stat_copy(stat_type)

        calced_iv_set.suggestion.update_lvl = _get_update_lvl(stat, calced_iv_set.values)

        # noinspection PyUnresolvedReferences
        if calced_iv_set.suggestion.update_lvl != sample.lvl + 1:
            calced_iv_set.suggestion.delta_ev = _get_delta_ev(stat, calced_iv_set.values)
        else:
            calced_iv_set.suggestion.delta_ev = 0


def _get_update_lvl(stat: Stat, iv_set: set[int]) -> Optional[int]:
    if len(iv_set) < 2:
        # No suggestion possible.
        return None

    min_iv, max_iv = min(iv_set), max(iv_set)
    # noinspection PyTypeChecker
    cur_lvl: int = stat.lvl
    for lvl in range(cur_lvl + 1, LVL_RANGE.max + 1):
        if stat.get_val(lvl=lvl, iv=min_iv) != stat.get_val(lvl=lvl, iv=max_iv):
            return lvl

    # No suggestion found :(
    return None


def _get_delta_ev(stat: Stat, iv_set: set[int]) -> Optional[int]:
    if len(iv_set) < 2:
        # No suggestion possible.
        return None

    min_iv, max_iv = min(iv_set), max(iv_set)
    # noinspection PyUnresolvedReferences
    lvl: int = stat.lvl + 1
    # noinspection PyTypeChecker
    cur_ev: int = stat.ev
    # Yes, it makes sense to check only multiples of 4 here, but let's not
    # handle stat calculation here and leave it encapsulated in `Stat`.
    for ev in range(cur_ev + 1, Stat.EV_RANGE.max + 1):
        if stat.get_val(lvl=lvl, iv=min_iv, ev=ev) != stat.get_val(lvl=lvl, iv=max_iv, ev=ev):
            return ev - cur_ev

    # No suggestion found :(
    return None


def _mid_iv_ranker(iv_set: set[int]) -> float:
    return sum(iv_set) / len(iv_set)


type ColorMode = Literal["min", "mid", "max"]


def pprint_iv_sets(
    iv_sets: CalcedIVSets_T,
    color_mode: ColorMode = "mid",
    important_stat_types: Optional[Container[StatType]] = None,
) -> None:
    if color_mode == "min":
        ranker = min
    elif color_mode == "mid":
        ranker = _mid_iv_ranker
    elif color_mode == "max":
        ranker = max
    else:
        raise RuntimeError(f"Unsupported {color_mode=!r}")

    if important_stat_types is None:
        important_stat_types = set(StatType)
    # Important stats will be colored according to their IVs.

    max_stat_type_len = max(len(stat_type.name) for stat_type in StatType)
    max_iv_set_len = max(len(str(calced_iv_set.values)) for calced_iv_set in iv_sets.values())

    for stat_type, calced_iv_set in iv_sets.items():
        iv_set = calced_iv_set.values
        suggestion = calced_iv_set.suggestion
        update_lvl, delta_ev = suggestion.update_lvl, suggestion.delta_ev

        color, on_color = None, None
        if stat_type not in important_stat_types:
            color = "dark_grey"
        elif len(iv_set) == 1 and next(iter(iv_set)) == Stat.IV_RANGE.max:
            on_color = "on_green"        # exactly highest
        elif (rank := ranker(iv_set)) == Stat.IV_RANGE.max:
            # It can appear only for `color_mode='max'`.
            color = "light_green"        # highest
        elif rank <= Stat.IV_RANGE.max / 5:
            color = "light_red"          # 0
        elif rank <= Stat.IV_RANGE.max * 2 / 5:
            color = "light_yellow"       # 1
        elif rank <= Stat.IV_RANGE.max * 3 / 5:
            color = "light_magenta"      # 2
        elif rank <= Stat.IV_RANGE.max * 4 / 5:
            color = "light_blue"         # 3
        else:
            color = "light_cyan"         # 4

        print(colored(
            f"{stat_type:{max_stat_type_len}}: {str(sorted(iv_set)):{max_iv_set_len}},"
            f" update_lvl={str(update_lvl):4}, {delta_ev=}",
            color=color,
            on_color=on_color
        ))


def main():

    iv_sets = get_iv_sets(
        Pokemon.TOTODILE,
        obs_stats=[
            {"lvl": 5, "stats": {
                StatType.HP: {"value": 21, "ev": 0},
                StatType.ATK: {"value": 13, "ev": 0},
                StatType.DEF: {"value": 11, "ev": 0},
                StatType.SPATK: {"value": 10, "ev": 0},
                StatType.SPDEF: {"value": 10, "ev": 0},
                StatType.SPEED: {"value": 9, "ev": 0}
            }},
            {"lvl": 6, "stats": {
                StatType.HP: {"value": 23, "ev": 0},
                StatType.ATK: {"value": 14, "ev": 0},
                StatType.DEF: {"value": 12, "ev": 0},
                StatType.SPATK: {"value": 11, "ev": 0},
                StatType.SPDEF: {"value": 11, "ev": 0},
                StatType.SPEED: {"value": 9, "ev": 0}
            }},
            {"lvl": 7, "stats": {
                StatType.HP: {"value": 25, "ev": 0},
                StatType.ATK: {"value": 15, "ev": 0},
                StatType.DEF: {"value": 13, "ev": 0},
                StatType.SPATK: {"value": 12, "ev": 0},
                StatType.SPDEF: {"value": 12, "ev": 0},
                StatType.SPEED: {"value": 10, "ev": 20}
            }},
        ],
        nature=Nature.BRAVE,
        characteristic=Characteristic.ALERT_TO_SOUNDS,
    )

    pprint_iv_sets(iv_sets)


if __name__ == "__main__":
    main()
