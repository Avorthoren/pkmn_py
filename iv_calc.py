import operator
from functools import reduce
from typing import Optional, Iterable, TypedDict

from characteristic import Characteristic
from nature import Nature
from pkmn_stat import StatType, Stat, StatsData, InputStatsData_T
from pokemon import Species_T, Sample, NatureIVSets_T, Pokemon
from utils import colored


class ObsStat(TypedDict):
    lvl: int
    stats: StatsData | InputStatsData_T


def get_iv_sets(
    spec: Species_T,
    obs_stats: Iterable[ObsStat],
    nature: Nature = None,
    characteristic: Characteristic = None,
    name: str = None
) -> NatureIVSets_T:
    iv_sets = {
        stat_type: set(Stat.IV_RANGE)
        for stat_type in StatType
    }

    for obs_stats_sample in obs_stats:
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
        # And finally - intersect with current state of sets:
        for stat_type in StatType:
            iv_sets[stat_type] &= sample_merged_iv_sets[stat_type]

    return iv_sets


def pprint_iv_sets(iv_sets: NatureIVSets_T) -> None:
    for stat_type, iv_set in iv_sets.items():
        mid = sum(iv_set) / len(iv_set)
        if mid == Stat.IV_RANGE.max:
            color = "green"
        elif mid <= Stat.IV_RANGE.max / 6:
            color = "red"
        elif mid <= Stat.IV_RANGE.max * 2 / 6:
            color = "yellow"
        elif mid <= Stat.IV_RANGE.max * 3 / 6:
            color = "magenta"
        elif mid <= Stat.IV_RANGE.max * 4 / 6:
            color = "white"
        elif mid <= Stat.IV_RANGE.max * 5 / 6:
            color = "blue"
        else:
            color = "cyan"

        print(colored(f"{stat_type}: {iv_set}", color))


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
