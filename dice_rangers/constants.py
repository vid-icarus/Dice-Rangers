# Board
GRID_SIZE = 8            # 8x8 grid
TILE_SIZE = 96           # pixels per tile
WINDOW_SIZE = 800        # window dimensions (800x800)
COLUMNS = "ABCDEFGH"     # column labels

# Morale
STARTING_MORALE = 20     # per team
MAX_MORALE = 20

# Movement
MOVEMENT_DIE = 6         # 1d6 for movement

# Combat
MELEE_DAMAGE_DIE = 6     # 1d6 melee
RANGED_DAMAGE_DIE = 4    # 1d4 ranged
DEFENSE_DIE = 4          # 1d4 defense
MAX_RANGED_DISTANCE = 3  # Chebyshev distance

# Items
HEAL_AMOUNT = 6
ATK_BOOST = 2
DEF_BOOST = 4

# Board Events
EVENT_DIE = 8            # 1d8 for board events
SPAWN_COORD_DIE = 8      # 1d8 for item spawn x and y

# Obstacle Placement
OBSTACLES_PER_PLAYER = 4
OBSTACLE_COORD_DIE = 8   # 2d8 for obstacle target

# Spawn Zones
P1_SPAWN_ROWS = (1, 2, 3)
P2_SPAWN_ROWS = (6, 7, 8)

# Edge squares (obstacles cannot be placed here)
EDGE_ROWS = (1, 8)
EDGE_COLS = ("A", "H")
