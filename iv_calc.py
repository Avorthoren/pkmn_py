import operator
from functools import reduce
from typing import Optional, Iterable, TypedDict

from characteristic import Characteristic
from nature import Nature
from pkmn_stat import StatType, Stat, StatsData, InputStatsData_T
from pokemon import Species_T, Sample, NatureIVSets_T, Pokemon


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
            stat_type: reduce(operator.or_, (nature_iv_sets[stat_type] for nature_iv_sets in sample_iv_sets.values()))
            for stat_type in StatType
        }
        # And finally - intersect with current state of sets:
        for stat_type in StatType:
            iv_sets[stat_type] &= sample_merged_iv_sets[stat_type]

    return iv_sets


def main():

    iv_sets = get_iv_sets(
        Pokemon.TOTODILE,
        obs_stats=[
            {"lvl": 5, "stats": {
                StatType.HP: {"value": 20, "ev": 0},
                StatType.ATK: {"value": 12, "ev": 0},
                StatType.DEF: {"value": 11, "ev": 0},
                StatType.SPATK: {"value": 9, "ev": 0},
                StatType.SPDEF: {"value": 10, "ev": 0},
                StatType.SPEED: {"value": 8, "ev": 0}
            }},
        ],
        nature=Nature.BRAVE,
        characteristic=Characteristic.ALERT_TO_SOUNDS,
    )

    for stat_type, iv_set in iv_sets.items():
        print(stat_type, iv_set)


if __name__ == "__main__":
    main()
