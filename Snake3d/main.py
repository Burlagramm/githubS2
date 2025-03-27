from ursina import *
import random

app = Ursina()

# Game variables
GRID_SIZE = 20
MOVE_DELAY = 0.1
score = 0
game_over = False
paused = False
special_food_active = False
special_food_timer = 0
boost_active = False
boost_timer = 0
snake_color = color.green
snake_trail = []
trail_length = 10
current_level = 1
obstacles = []
bridges = []
food_types = [
    {"model": "sphere", "color": color.red, "growth": 1, "score": 10},
    {"model": "cube", "color": color.cyan, "growth": 2, "score": 20},
    {"model": "diamond", "color": color.magenta, "growth": 3, "score": 30}
]
current_food_type = 0
food_spawn_timer = 0

# Create game entities
snake = Entity(model='cube', color=snake_color, scale=(1, 1, 1), position=(0, 0, 0))
food = Entity(model='sphere', color=color.red, scale=(1, 1, 1), position=(5, 0, 0))
special_food = Entity(model='sphere', color=color.gold, scale=(1.2, 1.2, 1.2), position=(0, 0, 0))
special_food.disable()

# Snake segments
snake_segments = [snake]

# Movement direction
direction = Vec3(1, 0, 0)
next_direction = Vec3(1, 0, 0)

# Text elements
score_text = Text(text=f"Score: {score}", position=(-0.85, 0.45), scale=2)
level_text = Text(text=f"Level: {current_level}", position=(-0.85, 0.4), scale=2)
game_over_text = Text(text="GAME OVER\nPress R to restart", position=(0, 0), origin=(0, 0), scale=3, color=color.red)
game_over_text.disable()
pause_text = Text(text="PAUSED\nPress P to continue", position=(0, 0), origin=(0, 0), scale=3, color=color.yellow)
pause_text.disable()
boost_text = Text(text="SPEED BOOST!", position=(0, 0.3), origin=(0, 0), scale=2, color=color.orange)
boost_text.disable()

# Skybox and environment
sky = Sky()
ground = Entity(model='plane', scale=(GRID_SIZE + 2, 1, GRID_SIZE + 2), color=color.dark_gray, position=(0, 0, 0))

# Create border walls
walls = []
for x in range(-GRID_SIZE // 2 - 1, GRID_SIZE // 2 + 2):
    walls.append(Entity(model='cube', color=color.gray, position=(x, 0, -GRID_SIZE // 2 - 1)))
    walls.append(Entity(model='cube', color=color.gray, position=(x, 0, GRID_SIZE // 2 + 1)))
for z in range(-GRID_SIZE // 2 - 1, GRID_SIZE // 2 + 2):
    walls.append(Entity(model='cube', color=color.gray, position=(-GRID_SIZE // 2 - 1, 0, z)))
    walls.append(Entity(model='cube', color=color.gray, position=(GRID_SIZE // 2 + 1, 0, z)))

# Camera setup
camera.position = (0, 20, 0)
camera.rotation_x = 90


def generate_random_position():
    while True:
        x = random.randint(-GRID_SIZE // 2, GRID_SIZE // 2)
        z = random.randint(-GRID_SIZE // 2, GRID_SIZE // 2)

        # Check if position is occupied by snake or obstacles
        position_clear = True
        for segment in snake_segments:
            if segment.x == x and segment.z == z:
                position_clear = False
                break

        for obstacle in obstacles:
            if obstacle.x == x and obstacle.z == z:
                position_clear = False
                break

        if position_clear:
            return Vec3(x, 0, z)


def place_food():
    food.position = generate_random_position()


def place_special_food():
    global special_food_active, special_food_timer
    special_food.position = generate_random_position()
    special_food.enable()
    special_food_active = True
    special_food_timer = 10  # Special food stays for 10 seconds


def change_food_type():
    global current_food_type, food
    current_food_type = random.randint(0, len(food_types) - 1)
    food_type = food_types[current_food_type]
    food.model = food_type["model"]
    food.color = food_type["color"]
    place_food()


def setup_level(level):
    global current_level, MOVE_DELAY, obstacles, bridges

    # Clear previous obstacles
    for obstacle in obstacles:
        destroy(obstacle)
    obstacles = []

    # Clear previous bridges
    for bridge in bridges:
        destroy(bridge)
    bridges = []

    current_level = level
    level_text.text = f"Level: {current_level}"

    # Adjust difficulty
    MOVE_DELAY = max(0.04, 0.1 - (level - 1) * 0.01)

    # Add obstacles based on level
    num_obstacles = min(30, (level - 1) * 3)
    for _ in range(num_obstacles):
        pos = generate_random_position()
        obstacle = Entity(model='cube', color=color.brown, position=pos)
        obstacles.append(obstacle)

    # Add bridges based on level
    num_bridges = min(5, level)
    for _ in range(num_bridges):
        pos = generate_random_position()
        bridge = Entity(model='cube', color=color.rgba(0, 0.5, 1, 0.5), scale=(3, 0.5, 1), position=pos)
        bridges.append(bridge)


def move_snake():
    global score, game_over, special_food_active, special_food_timer, boost_active, boost_timer, snake_color, current_level

    if game_over or paused:
        return

    # Update direction
    direction.x = next_direction.x
    direction.z = next_direction.z

    # Calculate new head position
    new_head_pos = snake_segments[0].position + direction

    # Check collision with self
    for segment in snake_segments[1:]:
        if segment.position == new_head_pos:
            game_end()
            return

    # Check if on bridge (skip obstacle and wall checks if true)
    on_bridge = False
    for bridge in bridges:
        # Köprünün alanını kontrol et (3 birim genişlik)
        if (abs(new_head_pos.x - bridge.x) <= 1.5 and
                abs(new_head_pos.z - bridge.z) <= 0.5):
            on_bridge = True
            break

    # Check collision with walls (skip if on bridge)
    if not on_bridge and (abs(new_head_pos.x) > GRID_SIZE // 2 or
                          abs(new_head_pos.z) > GRID_SIZE // 2):
        game_end()
        return

    # Check collision with obstacles (skip if on bridge)
    if not on_bridge:
        for obstacle in obstacles:
            if obstacle.position == new_head_pos:
                game_end()
                return

    # Create new head
    new_head = Entity(model='cube', color=snake_color, position=new_head_pos)
    snake_segments.insert(0, new_head)

    # Add visual trail effect
    if random.random() < 0.3:  # 30% chance to spawn trail particle
        trail = Entity(model='cube', color=snake_color.tint(-.2), scale=0.5, position=new_head_pos)
        snake_trail.append(trail)
        invoke(lambda t=trail: destroy(t), delay=0.5)

    # Check for food collision
    if new_head_pos == food.position:
        food_type = food_types[current_food_type]
        score += food_type["score"]
        score_text.text = f"Score: {score}"

        # Add growth segments based on food type
        for _ in range(food_type["growth"]):
            # Add a new segment at the current tail position
            tail_pos = snake_segments[-1].position
            new_segment = Entity(model='cube', color=snake_color, position=tail_pos)
            snake_segments.append(new_segment)

        place_food()
        food_spawn_timer = 2  # 2 saniye sonra yeni yiyecek

        # 20% chance to spawn special food after eating regular food
        if not special_food_active and random.random() < 0.2:
            place_special_food()

        # Level up after every 50 points
        if score % 50 == 0:
            setup_level(current_level + 1)
    elif special_food_active and new_head_pos == special_food.position:
        # Special food effects
        score += 30
        score_text.text = f"Score: {score}"
        special_food.disable()
        special_food_active = False

        # Activate speed boost
        boost_active = True
        boost_timer = 5  # 5 seconds boost
        boost_text.enable()
        snake_color = color.yellow
        for segment in snake_segments:
            segment.color = snake_color
    else:
        # Remove tail if no food was eaten
        tail = snake_segments.pop()
        destroy(tail)

    # Clean up old trail particles
    while len(snake_trail) > trail_length:
        old_trail = snake_trail.pop(0)
        destroy(old_trail)

    # Schedule next move
    if boost_active:
        invoke(move_snake, delay=MOVE_DELAY * 0.5)  # Move faster during boost
    else:
        invoke(move_snake, delay=MOVE_DELAY)


def update():
    global special_food_active, special_food_timer, boost_active, boost_timer, snake_color, food_spawn_timer

    if game_over or paused:
        return

    # Update special food timer
    if special_food_active:
        special_food_timer -= time.dt
        if special_food_timer <= 0:
            special_food.disable()
            special_food_active = False

    # Update boost timer
    if boost_active:
        boost_timer -= time.dt
        if boost_timer <= 0:
            boost_active = False
            boost_text.disable()
            snake_color = color.green
            for segment in snake_segments:
                segment.color = snake_color

    # Update food spawn timer
    food_spawn_timer -= time.dt
    if food_spawn_timer <= 0:
        change_food_type()
        food_spawn_timer = 2  # 2 saniye sonra yeni yiyecek


def input(key):
    global next_direction, game_over, paused

    if key == 'w' or key == 'up arrow':
        if direction.z != 1:  # Prevent 180-degree turns
            next_direction = Vec3(0, 0, 1)  # Yukarı yön - negatif Z
    elif key == 's' or key == 'down arrow':
        if direction.z != -1:
            next_direction = Vec3(0, 0, -1)  # Aşağı yön - pozitif Z
    elif key == 'a' or key == 'left arrow':
        if direction.x != 1:
            next_direction = Vec3(-1, 0, 0)  # Sol yön - negatif X
    elif key == 'd' or key == 'right arrow':
        if direction.x != -1:
            next_direction = Vec3(1, 0, 0)  # Sağ yön - pozitif X
    elif key == 'r' and game_over:
        restart_game()
    elif key == 'p':
        toggle_pause()
    elif key == 'c':
        # Camera toggle between top-down and behind-snake view
        if camera.rotation_x == 90:  # Top-down view
            camera.position = snake_segments[0].position + Vec3(0, 5, 10)
            camera.rotation_x = 30
            camera.look_at(snake_segments[0])
        else:  # Behind-snake view
            camera.position = Vec3(0, 20, 0)
            camera.rotation_x = 90


def toggle_pause():
    global paused
    paused = not paused
    if paused:
        pause_text.enable()
    else:
        pause_text.disable()
        invoke(move_snake, delay=MOVE_DELAY)


def game_end():
    global game_over
    game_over = True
    game_over_text.enable()

    # Yılanı kırmızıya döndürerek yanma efekti ver
    for segment in snake_segments:
        segment.color = color.red
        # Yanma animasyonu için parçacık efektleri
        for _ in range(3):
            spark = Entity(model='cube', color=color.yellow, scale=0.3,
                           position=segment.position + Vec3(random.uniform(-0.5, 0.5),
                                                            random.uniform(0, 1),
                                                            random.uniform(-0.5, 0.5)))
            destroy(spark, delay=0.5)


def restart_game():
    global snake_segments, score, game_over, direction, next_direction, snake_color, special_food_active, boost_active

    # Reset game state
    game_over = False
    score = 0
    game_over_text.disable()

    # Reset direction
    direction = Vec3(1, 0, 0)
    next_direction = Vec3(1, 0, 0)

    # Reset colors and effects
    snake_color = color.white
    special_food_active = False
    boost_active = False
    boost_text.disable()
    special_food.disable()

    # Remove old snake segments
    for segment in snake_segments:
        destroy(segment)

    # Clean up trails
    for trail in snake_trail:
        destroy(trail)
    snake_trail.clear()

    # Remove old bridges
    for bridge in bridges:
        destroy(bridge)
    bridges.clear()

    # Create new snake
    snake = Entity(model='cube', color=snake_color, position=(0, 0, 0))
    snake_segments = [snake]

    # Reset score
    score_text.text = f"Score: {score}"

    # Setup level 1
    setup_level(1)

    # Place food
    place_food()

    # Start movement
    invoke(move_snake, delay=MOVE_DELAY)


# Setup initial level
setup_level(1)

# Start the game
invoke(move_snake, delay=MOVE_DELAY)
food_spawn_timer = 2  # İlk yemek 2 saniye sonra değişecek

# Instructions
instruction_text = dedent('''
    Controls:
    WASD or Arrow Keys - Move
    P - Pause
    R - Restart
    C - Toggle Camera View
''').strip()
Text(text=instruction_text, position=(0.6, 0.4), scale=1.5)

app.run()