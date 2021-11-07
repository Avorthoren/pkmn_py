from characteristic import Characteristic
from nature import Nature
from pokemon import Pokemon, Representative
from pkmn_stat import StatType
from utils import pretty_print


def main():
	r = Representative(
		spec=Pokemon.MAGIKARP,
		lvl=7,
		nature=Nature.ADAMANT,
		characteristic=Characteristic.LIKES_TO_TRASH_ABOUT,
		stats={
			StatType.HP: {"value": 19},
			StatType.ATK: {"value": 8},
			StatType.DEF: {"value": 13},
			StatType.SPATK: {"value": 7},
			StatType.SPDEF: {"value": 7},
			StatType.SPEED: {"value": 17}
		}
	)

	iv_sets = r.get_iv_sets()
	pretty_print(iv_sets)
	# for stat_type, iv_set in iv_sets.items():
	# 	print(f"{stat_type.name}: {iv_set}")


if __name__ == "__main__":
	main()
