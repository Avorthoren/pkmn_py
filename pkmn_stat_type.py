from utils import SEnum, enum


class StatType(SEnum):
	HP = 1
	ATK = 2
	DEF = 3
	SPATK = 4
	SPDEF = 5
	SPEED = 6


class GenStatType(SEnum):
	ATK = enum.auto()
	DUR = enum.auto()    # HP * DEF
	SPATK = enum.auto()
	SPDUR = enum.auto()  # HP * SPDEF
	SPEED = enum.auto()
