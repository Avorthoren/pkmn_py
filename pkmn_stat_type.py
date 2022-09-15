from utils import SEnum, enum


class StatType(SEnum):
	HP = 1
	ATK = 2
	DEF = 3
	SPATK = 4
	SPDEF = 5
	SPEED = 6


class GenStatType(SEnum):
	ATTACK = enum.auto()
	DURABILITY = enum.auto()    # HP * DEF
	SPATTACK = enum.auto()
	SPDURABILITY = enum.auto()  # HP * SPDEF
	SPEED = enum.auto()
