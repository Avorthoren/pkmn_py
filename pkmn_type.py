from fractions import Fraction

from utils import SEnum, enum, enum_const_dict, pretty_print


class Type(SEnum):
	NORMAL = enum.auto()
	FIGHTING = enum.auto()
	FLYING = enum.auto()
	POISON = enum.auto()
	GROUND = enum.auto()
	ROCK = enum.auto()
	BUG = enum.auto()
	GHOST = enum.auto()
	STEEL = enum.auto()
	FIRE = enum.auto()
	WATER = enum.auto()
	GRASS = enum.auto()
	ELECTRIC = enum.auto()
	PSYCHIC = enum.auto()
	ICE = enum.auto()
	DRAGON = enum.auto()
	DARK = enum.auto()
	FAIRY = enum.auto()
	# Defence can be typeless when pokemon loses all its types (after using
	# Burn Up or Roost, for example). Attacks can be typeless as well: Struggle,
	# for example. For more details:
	# https://bulbapedia.bulbagarden.net/wiki/Type#Typeless
	NONE = enum.auto()


class DefTypeEff(SEnum):
	WEAK = Fraction(2)
	REGULAR = Fraction(1)
	RESISTANT = Fraction(1, 2)
	IMMUNE = Fraction(0)
	DEFAULT = REGULAR


_DefTypesEfficiencyCondensed = enum_const_dict(Type, {DefTypeEff: {Type}})

# Only multipliers other than REGULAR are described here.
_DEF_EFF_CONDENSED = _DefTypesEfficiencyCondensed({
	Type.NORMAL: {
		DefTypeEff.WEAK: {Type.FIGHTING},
		DefTypeEff.IMMUNE: {Type.GHOST}
	},
	Type.FIGHTING: {
		DefTypeEff.WEAK: {Type.FLYING, Type.PSYCHIC, Type.FAIRY},
		DefTypeEff.RESISTANT: {Type.ROCK, Type.BUG, Type.DARK}
	},
	Type.FLYING: {
		DefTypeEff.WEAK: {Type.ROCK, Type.ELECTRIC, Type.ICE},
		DefTypeEff.RESISTANT: {Type.FIGHTING, Type.BUG, Type.GRASS},
		DefTypeEff.IMMUNE: {Type.GROUND}
	},
	Type.POISON: {
		DefTypeEff.WEAK: {Type.GROUND, Type.PSYCHIC},
		DefTypeEff.RESISTANT: {Type.FIGHTING, Type.POISON, Type.BUG, Type.GRASS, Type.FAIRY}
	},
	Type.GROUND: {
		DefTypeEff.WEAK: {Type.WATER, Type.GRASS, Type.ICE},
		DefTypeEff.RESISTANT: {Type.POISON, Type.ROCK},
		DefTypeEff.IMMUNE: {Type.ELECTRIC}
	},
	Type.ROCK: {
		DefTypeEff.WEAK: {Type.FIGHTING, Type.GROUND, Type.STEEL, Type.WATER, Type.GRASS},
		DefTypeEff.RESISTANT: {Type.NORMAL, Type.FLYING, Type.POISON, Type.FIRE}
	},
	Type.BUG: {
		DefTypeEff.WEAK: {Type.FLYING, Type.ROCK, Type.FIRE},
		DefTypeEff.RESISTANT: {Type.FIGHTING, Type.GROUND, Type.GRASS}
	},
	Type.GHOST: {
		DefTypeEff.WEAK: {Type.GHOST, Type.DARK},
		DefTypeEff.RESISTANT: {Type.POISON, Type.BUG},
		DefTypeEff.IMMUNE: {Type.NORMAL, Type.FIGHTING}
	},
	Type.STEEL: {
		DefTypeEff.WEAK: {Type.FIGHTING, Type.GROUND, Type.FIRE},
		DefTypeEff.RESISTANT: {
			Type.NORMAL, Type.FLYING, Type.ROCK, Type.BUG, Type.STEEL,
			Type.GRASS, Type.PSYCHIC, Type.ICE, Type.DRAGON, Type.FAIRY
		},
		DefTypeEff.IMMUNE: {Type.POISON}
	},
	Type.FIRE: {
		DefTypeEff.WEAK: {Type.GROUND, Type.ROCK, Type.WATER},
		DefTypeEff.RESISTANT: {Type.BUG, Type.STEEL, Type.FIRE, Type.GRASS, Type.ICE, Type.FAIRY}
	},
	Type.WATER: {
		DefTypeEff.WEAK: {Type.GRASS, Type.ELECTRIC},
		DefTypeEff.RESISTANT: {Type.STEEL, Type.FIRE, Type.WATER, Type.ICE}
	},
	Type.GRASS: {
		DefTypeEff.WEAK: {Type.FLYING, Type.POISON, Type.BUG, Type.FIRE, Type.ICE},
		DefTypeEff.RESISTANT: {Type.GROUND, Type.WATER, Type.GRASS, Type.ELECTRIC}
	},
	Type.ELECTRIC: {
		DefTypeEff.WEAK: {Type.GROUND},
		DefTypeEff.RESISTANT: {Type.FLYING, Type.STEEL, Type.ELECTRIC}
	},
	Type.PSYCHIC: {
		DefTypeEff.WEAK: {Type.BUG, Type.GHOST, Type.DARK},
		DefTypeEff.RESISTANT: {Type.FIGHTING, Type.PSYCHIC}
	},
	Type.ICE: {
		DefTypeEff.WEAK: {Type.FIGHTING, Type.ROCK, Type.STEEL, Type.FIRE},
		DefTypeEff.RESISTANT: {Type.ICE}
	},
	Type.DRAGON: {
		DefTypeEff.WEAK: {Type.ICE, Type.DRAGON, Type.FAIRY},
		DefTypeEff.RESISTANT: {Type.FIRE, Type.WATER, Type.GRASS, Type.ELECTRIC}
	},
	Type.DARK: {
		DefTypeEff.WEAK: {Type.FIGHTING, Type.BUG, Type.FAIRY},
		DefTypeEff.RESISTANT: {Type.GHOST, Type.DARK},
		DefTypeEff.IMMUNE: {Type.PSYCHIC}
	},
	Type.FAIRY: {
		DefTypeEff.WEAK: {Type.POISON, Type.STEEL},
		DefTypeEff.RESISTANT: {Type.FIGHTING, Type.BUG, Type.DARK},
		DefTypeEff.IMMUNE: {Type.DRAGON}
	},
	Type.NONE: {}
})

# Construct effectiveness dict for each defence type.
# `DEF_EFF[dt][at]` is multiplier when `dt` is attacked by `at`.
DEF_EFF = {}
for dt in Type:
	dt_eff = {}
	dt_eff_cond = _DEF_EFF_CONDENSED[dt]
	for at in Type:
		eff = DefTypeEff.DEFAULT
		definitions = 0
		for e, types in dt_eff_cond.items():
			if at in types:
				eff = e
				definitions += 1

		if definitions > 1:
			raise RuntimeError(
				f"Defence type {dt} and attack type {at} pair have multiple definitions of effectiveness"
			)

		dt_eff[at] = eff

	DEF_EFF[dt] = dt_eff

# Construct effectiveness dict for each attack type.
# `ATK_EFF[at][dt]` is multiplier when `at` attacks `dt`.
ATK_EFF = {
	at: {dt: DEF_EFF[dt][at] for dt in Type}
	for at in Type
}


def main():
	pretty_print(ATK_EFF)


if __name__ == "__main__":
	main()
