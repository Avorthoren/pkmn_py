from characteristic import Characteristic
from nature import Nature
from pokemon import Pokemon, Representative
from pkmn_stat_type import StatType
from utils import pretty_print


def main():
	r = Representative(
		spec=Pokemon.MEGA_RAYQUAZA,
		lvl=70,
		stats={
			StatType.HP: {"value": 248},
			StatType.ATK: {"value": 257, "ev": 5},
			StatType.DEF: {"value": 182},
			StatType.SPATK: {"value": 278},
			StatType.SPDEF: {"value": 159, "ev": 5},
			StatType.SPEED: {"value": 154, "ev": 2}
		}
	)

	iv_sets = r.get_iv_sets()
	pretty_print(iv_sets)

# {
#     "Nature.LAX": {
#         "HP": "{30, 31}",
#         "ATK": "{0, 1}",
#         "DEF": "{30, 31}",
#         "SPATK": "{30, 31}",
#         "SPDEF": "{20, 21}",
#         "SPEED": "{9}"
#     }
# }


if __name__ == "__main__":
	main()
