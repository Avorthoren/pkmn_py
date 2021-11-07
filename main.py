from characteristic import Characteristic
from nature import Nature
from pokemon import Pokemon, Representative
from pkmn_stat import StatType


def main():
	r = Representative(
		spec=Pokemon.MAGIKARP,
		lvl=25,
		nature=Nature.ADAMANT,
		characteristic=Characteristic.LIKES_TO_TRASH_ABOUT,
		stats={
			StatType.HP: {"value": 51},
			StatType.ATK: {"value": 17},
			StatType.DEF: {"value": 39},
			StatType.SPATK: {"value": 15},
			StatType.SPDEF: {"value": 18},
			StatType.SPEED: {"value": 51}
		}
	)

	ivSets = r.getIVSets()

	for statType, ivSet in ivSets.items():
		print(f"{statType.name}: {ivSet}")



if __name__ == "__main__":
	main()