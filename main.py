from characteristic import Characteristic
from nature import Nature
from pokemon import Pokemon, Representative
from pkmn_stat import StatType


def main():
	# lvl = 78
	# nature = Nature.ADAMANT

	# stats = [
	# 	Stat(StatType.HP,    base=108, iv=24, lvl=lvl, ev=74),
	# 	Stat(StatType.ATK,   base=130, iv=12, lvl=lvl, ev=190, mult=1.1),
	# 	Stat(StatType.DEF,   base=95,  iv=30, lvl=lvl, ev=91),
	# 	Stat(StatType.SPATK, base=80,  iv=16, lvl=lvl, ev=48,  mult=0.9),
	# 	Stat(StatType.SPDEF, base=85,  iv=23, lvl=lvl, ev=84),
	# 	Stat(StatType.SPEED, base=102, iv=5,  lvl=lvl, ev=23)
	# ]
	# for stat in stats:
	# 	print(f"{stat._type.name}: {stat.getVal(lvl)}")
	#
	# stats = [
	# 	Stat(StatType.HP,    base=108, val=289, lvl=lvl, ev=74),              # 24
	# 	Stat(StatType.ATK,   base=130, val=278, lvl=lvl, ev=190, mult=1.1),   # 12
	# 	Stat(StatType.DEF,   base=95,  val=193, lvl=lvl, ev=91),              # 30
	# 	Stat(StatType.SPATK, base=80,  val=135, lvl=lvl, ev=48,  mult=0.9),   # 16
	# 	Stat(StatType.SPDEF, base=85,  val=171, lvl=lvl, ev=84),              # 23
	# 	Stat(StatType.SPEED, base=102, val=171, lvl=lvl, ev=23)               # 5
	# ]
	#
	# for stat in stats:
	# 	print(f"{stat._type.name}: {stat.getIVRange()}")

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