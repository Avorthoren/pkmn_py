from characteristic import Characteristic
from nature import Nature
from pokemon import Pokemon, Representative
from pkmn_stat_type import StatType
from utils import pretty_print


def main():
	# r = Representative(
	# 	spec=Pokemon.RAYQUAZA,
	# 	lvl=70,
	# 	stats={
	# 		StatType.HP: {"value": 248},
	# 		StatType.ATK: {"value": 237, "ev": 6},
	# 		StatType.DEF: {"value": 145},
	# 		StatType.SPATK: {"value": 236, "ev": 1},
	# 		StatType.SPDEF: {"value": 168, "ev": 5},
	# 		StatType.SPEED: {"value": 130, "ev": 3}
	# 	}
	# )

	r = Representative(
		spec=Pokemon.TOTODILE,
		lvl=5,
		nature=Nature.BRAVE,
		characteristic=Characteristic.ALERT_TO_SOUNDS,
		stats={
			StatType.HP: {"value": 21},
			StatType.ATK: {"value": 13},
			StatType.DEF: {"value": 11},
			StatType.SPATK: {"value": 10},
			StatType.SPDEF: {"value": 10},
			StatType.SPEED: {"value": 9}
		}
	)

	iv_sets = r.get_iv_sets()
	pretty_print(iv_sets)


if __name__ == "__main__":
	main()
