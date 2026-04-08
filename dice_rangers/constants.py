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

# Display — derived layout
FPS = 30
GRID_PIXEL_SIZE = TILE_SIZE * GRID_SIZE       # 768
GRID_ORIGIN_X = (WINDOW_SIZE - GRID_PIXEL_SIZE) // 2  # 16
GRID_ORIGIN_Y = (WINDOW_SIZE - GRID_PIXEL_SIZE) // 2  # 16

# Colors (RGB 3-tuples for standard Pygame drawing)
COLOR_BG = (30, 30, 40)
COLOR_GRID_LIGHT = (200, 200, 180)
COLOR_GRID_DARK = (160, 160, 140)
COLOR_GRID_LINE = (80, 80, 80)
COLOR_OBSTACLE = (60, 60, 70)
COLOR_ITEM_HEAL = (50, 200, 50)
COLOR_ITEM_ATK = (200, 50, 50)
COLOR_ITEM_DEF = (50, 100, 200)
COLOR_TEXT = (240, 240, 240)
COLOR_TEXT_DIM = (150, 150, 150)
COLOR_P1 = (80, 150, 255)
COLOR_P2 = (255, 100, 80)
COLOR_MORALE_BG = (40, 40, 50)
COLOR_BUTTON = (70, 70, 90)
COLOR_BUTTON_HOVER = (90, 90, 120)
COLOR_BUTTON_DISABLED = (50, 50, 60)

# Highlight colors — RGBA 4-tuples
# (used ONLY with per-pixel-alpha surfaces in draw_highlights)
COLOR_HIGHLIGHT_MOVE = (100, 200, 100, 120)
COLOR_HIGHLIGHT_ATTACK = (200, 80, 80, 120)
COLOR_HIGHLIGHT_SELECT = (100, 100, 255, 120)
COLOR_HIGHLIGHT_DROP = (200, 200, 80, 120)
COLOR_BANNER_BG = (20, 20, 30, 200)

# Unit/item placeholder sizes
UNIT_RADIUS = 36
ITEM_RADIUS = 14
OBSTACLE_PADDING = 4
