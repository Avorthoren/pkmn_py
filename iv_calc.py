from typing import Optional, Iterable

from characteristic import Characteristic
from nature import Nature
from pkmn_stat import StatsData, InputStatsData_T
from pokemon import Species_T


def get_iv_sets(
    spec: Species_T,
    stats: Iterable[tuple[int, StatsData | InputStatsData_T]],
    nature: Nature = None,
    characteristic: Characteristic = None,
    name: str = None
):