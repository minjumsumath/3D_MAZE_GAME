from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random, math, time


camera_pos = (0, 400, 400)
fovY = 90
GRID_LENGTH = 600
MAZE_SIZE = 15
CELL_SIZE = 40

maze = [[1 for _ in range(MAZE_SIZE)] for _ in range(MAZE_SIZE)]
player_pos = [1, 1]
PLAYER_RADIUS = CELL_SIZE * 0.4

game_time = 0
enemies = []

abilities = {"sprint": 3, "invis": 2, "shield": 2}
ability_timers = {"sprint": 0, "invis": 0, "shield": 0}
ability_cooldowns = {"sprint": 0, "invis": 0, "shield": 0}

slow_motion = False
invisible = False
shielded = False

player_health = 100
player_lives = 3

score = 0
coins_collected = 0
total_coins = 12

START_POS = [1, 1]
END_POS = [13, 13]

game_won = False
game_over = False

puzzles = []
high_risk_zones = []
coins = []



class Enemy:
    def __init__(self, x, z):
        self.pos = [x, z]
        self.patrol_path = self.generate_patrol_path(x, z)
        self.patrol_index = 0
        self.state = "patrol"  # patrol or chase
        self.last_seen_player = None
        self.alert_timer = 0
        self.hit_count = 0
        self.alive = True

    def generate_patrol_path(self, x, z):
        path = [(x, z)]
        for _ in range(4):
            dx, dz = random.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])
            nx, nz = x + dx * 2, z + dz * 2
            if 0 <= nx < MAZE_SIZE and 0 <= nz < MAZE_SIZE and maze[nx][nz] == 0:
                path.append((nx, nz))
                x, z = nx, nz
        return path

    def move_towards(self, tx, tz):
        speed = 0.01
        if self.pos[0] < tx:
            self.pos[0] = min(MAZE_SIZE - 1, self.pos[0] + speed)
        elif self.pos[0] > tx:
            self.pos[0] = max(0, self.pos[0] - speed)
        if self.pos[1] < tz:
            self.pos[1] = min(MAZE_SIZE - 1, self.pos[1] + speed)
        elif self.pos[1] > tz:
            self.pos[1] = max(0, self.pos[1] - speed)

    def update(self, player_x, player_z):
        if not self.alive:
            return

        self.alert_timer = max(0, self.alert_timer - 1)

        dist = math.sqrt((self.pos[0] - player_x) ** 2 + (self.pos[1] - player_z) ** 2)

        if dist < 4 and not invisible and self.alert_timer == 0:
            self.state = "chase"
            self.last_seen_player = (player_x, player_z)
            self.alert_timer = 300

        if self.state == "patrol":
            if self.patrol_path:
                target = self.patrol_path[self.patrol_index]
                if abs(self.pos[0] - target[0]) < 0.5 and abs(self.pos[1] - target[1]) < 0.5:
                    self.patrol_index = (self.patrol_index + 1) % len(self.patrol_path)
                else:
                    self.move_towards(target[0], target[1])

        elif self.state == "chase":
            if self.last_seen_player:
                lx, lz = self.last_seen_player
                if math.sqrt((self.pos[0] - lx) ** 2 + (self.pos[1] - lz) ** 2) < 1.5:
                    self.state = "patrol"
                else:
                    self.move_towards(lx, lz)
            else:
                self.state = "patrol"



def sphere_cube_collision(px, pz, radius=PLAYER_RADIUS):
    for x in range(MAZE_SIZE):
        for z in range(MAZE_SIZE):
            if maze[x][z] == 1:
                wx = (x - MAZE_SIZE / 2) * CELL_SIZE
                wz = (z - MAZE_SIZE / 2) * CELL_SIZE
                dist = ((px - wx) ** 2 + (pz - wz) ** 2) ** 0.5
                if dist < radius + CELL_SIZE * 0.5:
                    return True
    return False


def can_move(nx, nz):
    if not (0 <= nx < MAZE_SIZE and 0 <= nz < MAZE_SIZE and maze[nx][nz] != 1):
        return False
    px = (nx - MAZE_SIZE / 2) * CELL_SIZE
    pz = (nz - MAZE_SIZE / 2) * CELL_SIZE
    return not sphere_cube_collision(px, pz)


def check_enemy_collision():
    global player_health, player_lives, game_over

    px = (player_pos[0] - MAZE_SIZE / 2) * CELL_SIZE
    pz = (player_pos[1] - MAZE_SIZE / 2) * CELL_SIZE

    for enemy in enemies:
        if not enemy.alive:
            continue

        ex = (enemy.pos[0] - MAZE_SIZE / 2) * CELL_SIZE
        ez = (enemy.pos[1] - MAZE_SIZE / 2) * CELL_SIZE
        dist = ((px - ex) ** 2 + (pz - ez) ** 2) ** 0.5

        if dist < PLAYER_RADIUS + CELL_SIZE * 0.3:

            if not shielded:
                player_health -= 33
                if player_health <= 33:
                    player_lives -= 1
                    player_health = 100
                if player_lives <= 0:
                    game_over = True


            enemy.hit_count += 1
            if enemy.hit_count >= 3:
                enemy.alive = False
            return True

    return False



def update_dynamic_maze():
    global maze, game_time, high_risk_zones

    game_time += 1

    if game_time % 300 == 0:
        x, z = random.randint(2, MAZE_SIZE - 3), random.randint(2, MAZE_SIZE - 3)
        if random.random() > 0.6:
            maze[x][z] = 1 - maze[x][z]

    if game_time % 450 == 0:
        x, z = random.randint(4, MAZE_SIZE - 5), random.randint(4, MAZE_SIZE - 5)
        if maze[x][z] == 0 and random.random() > 0.8:
            maze[x][z] = 2
            high_risk_zones.append((x, z))


def generate_maze():
    global maze, player_pos, coins, score, coins_collected
    global game_won, game_over, enemies, puzzles, game_time
    global player_health, player_lives, high_risk_zones

    maze = [[1 for _ in range(MAZE_SIZE)] for _ in range(MAZE_SIZE)]

    def force_path_to_end(sx, sz, ex, ez):
        cx, cz = sx, sz
        while cx != ex or cz != ez:
            maze[cx][cz] = 0
            if cx < ex:
                cx += 1
            elif cx > ex:
                cx -= 1
            elif cz < ez:
                cz += 1
            elif cz > ez:
                cz -= 1
        maze[ex][ez] = 0

    force_path_to_end(START_POS[0], START_POS[1], END_POS[0], END_POS[1])

    def carve(x, z):
        maze[x][z] = 0
        dirs = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        random.shuffle(dirs)
        for dx, dz in dirs:
            nx, nz = x + dx * 2, z + dz * 2
            if 0 <= nx < MAZE_SIZE and 0 <= nz < MAZE_SIZE and maze[nx][nz] == 1:
                maze[x + dx][z + dz] = 0
                carve(nx, nz)

    path_points = []
    x, z = START_POS[0], START_POS[1]
    while x != END_POS[0] or z != END_POS[1]:
        path_points.append((x, z))
        if x < END_POS[0]:
            x += 1
        elif x > END_POS[0]:
            x -= 1
        elif z < END_POS[1]:
            z += 1
        elif z > END_POS[1]:
            z -= 1
    path_points.append((END_POS[0], END_POS[1]))

    for px, pz in path_points[::3]:
        carve(px, pz)

    enemies.clear()
    num_enemies = random.choice([3, 4])
    while len(enemies) < num_enemies:
        ex, ez = random.randint(3, MAZE_SIZE - 4), random.randint(3, MAZE_SIZE - 4)
        if maze[ex][ez] == 0:
            enemies.append(Enemy(ex, ez))

    puzzles.clear()
    for _ in range(4):
        px, pz = random.randint(3, MAZE_SIZE - 4), random.randint(3, MAZE_SIZE - 4)
        if maze[px][pz] == 0:
            puzzles.append({"pos": (px, pz), "activated": False})

    player_pos[:] = START_POS[:]
    score = 0
    coins_collected = 0
    game_won = False
    game_over = False
    player_health = 100
    player_lives = 3
    game_time = 0
    high_risk_zones = []

    place_coins()


def place_coins():
    global coins
    coins = []
    open_cells = [
        (x, z)
        for x in range(MAZE_SIZE)
        for z in range(MAZE_SIZE)
        if maze[x][z] == 0 and (x, z) not in [(START_POS[0], START_POS[1]), (END_POS[0], END_POS[1])]
    ]
    if len(open_cells) >= total_coins:
        coins = random.sample(open_cells, total_coins)


def collect_coins(nx, nz):
    global score, coins_collected, coins
    for i, (cx, cz) in enumerate(coins):
        if cx == nx and cz == nz:
            coins.pop(i)
            bonus = 20 if (nx, nz) in high_risk_zones else 10
            score += bonus
            coins_collected += 1
            return True
    return False



def use_ability(ability):
    global abilities, ability_timers, ability_cooldowns
    if abilities[ability] > 0 and ability_cooldowns[ability] <= 0:
        abilities[ability] -= 1
        ability_timers[ability] = 300
        ability_cooldowns[ability] = 600
        return True
    return False


def update_abilities():
    global ability_timers, ability_cooldowns, invisible, shielded
    for ability in ability_timers:
        if ability_timers[ability] > 0:
            ability_timers[ability] -= 1
        else:
            if ability == "invis":
                invisible = False
            if ability == "shield":
                shielded = False

        if ability_cooldowns[ability] > 0:
            ability_cooldowns[ability] -= 1



def check_puzzles(nx, nz):
    global score
    for puzzle in puzzles:
        if puzzle["pos"] == (nx, nz) and not puzzle["activated"]:
            puzzle["activated"] = True
            for dx in [-1, 0, 1]:
                for dz in [-1, 0, 1]:
                    tx, tz = nx + dx, nz + dz
                    if 0 <= tx < MAZE_SIZE and 0 <= tz < MAZE_SIZE and maze[tx][tz] == 1:
                        maze[tx][tz] = 0
            score += 50
            return True
    return False



def draw_text(x, y, text, font= GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def draw_maze():
    for x in range(MAZE_SIZE):
        for z in range(MAZE_SIZE):
            wx = (x - MAZE_SIZE / 2) * CELL_SIZE
            wz = (z - MAZE_SIZE / 2) * CELL_SIZE

            if maze[x][z] == 1:
                glColor3f(0.2, 0.2, 0.8)
                glPushMatrix()
                glTranslatef(wx, CELL_SIZE / 2, wz)
                glutSolidCube(CELL_SIZE)
                glPopMatrix()
            elif maze[x][z] == 2:
                glColor3f(0.8, 0.1, 0.1)
                glPushMatrix()
                glTranslatef(wx, CELL_SIZE * 0.05, wz)
                glutSolidCube(CELL_SIZE * 0.8)
                glPopMatrix()

            for puzzle in puzzles:
                if puzzle["pos"] == (x, z):
                    color = (0, 1, 0) if puzzle["activated"] else (0.7, 0.3, 1.0)
                    glColor3f(*color)
                    glPushMatrix()
                    glTranslatef(wx, CELL_SIZE * 0.2, wz)
                    glutSolidCube(CELL_SIZE * 0.6)
                    glPopMatrix()

    glColor3f(1, 0.2, 0.2)
    sx = (START_POS[0] - MAZE_SIZE / 2) * CELL_SIZE
    sz = (START_POS[1] - MAZE_SIZE / 2) * CELL_SIZE
    glPushMatrix()
    glTranslatef(sx, CELL_SIZE * 0.1, sz)
    glutSolidCube(CELL_SIZE * 0.8)
    glPopMatrix()

    glColor3f(1, 0.8, 0)
    ex = (END_POS[0] - MAZE_SIZE / 2) * CELL_SIZE
    ez = (END_POS[1] - MAZE_SIZE / 2) * CELL_SIZE
    glPushMatrix()
    glTranslatef(ex, CELL_SIZE * 0.1, ez)
    glutSolidCube(CELL_SIZE * 0.8)
    glPopMatrix()


def draw_player():
    if invisible:
        return
    color = (0, 1, 1) if shielded else (0, 1, 0)
    glColor3f(*color)
    px = (player_pos[0] - MAZE_SIZE / 2) * CELL_SIZE
    pz = (player_pos[1] - MAZE_SIZE / 2) * CELL_SIZE

    glPushMatrix()
    glTranslatef(px, CELL_SIZE / 2, pz)
    glutSolidSphere(PLAYER_RADIUS, 20, 20)
    glPopMatrix()


def draw_coins():
    glColor3f(1, 1, 0)
    for cx, cz in coins:
        coin_x = (cx - MAZE_SIZE / 2) * CELL_SIZE
        coin_z = (cz - MAZE_SIZE / 2) * CELL_SIZE
        glPushMatrix()
        glTranslatef(coin_x, CELL_SIZE * 0.3, coin_z)
        glutSolidSphere(CELL_SIZE * 0.1, 12, 12)
        glPopMatrix()


def draw_enemies():
    for enemy in enemies:
        if not enemy.alive:
            continue
        color = (0.5, 0.5, 0.2) if enemy.state == "chase" else (1, 0, 0)
        glColor3f(*color)
        ex = (enemy.pos[0] - MAZE_SIZE / 2) * CELL_SIZE
        ez = (enemy.pos[1] - MAZE_SIZE / 2) * CELL_SIZE
        glPushMatrix()
        glTranslatef(ex, CELL_SIZE / 2, ez)
        glutSolidCube(CELL_SIZE * 0.6)
        glPopMatrix()


def draw_lives():
    start_x = 850
    heart_size = 15
    for i in range(player_lives):
        x = start_x + i * (heart_size * 1.5)
        y = 760
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluOrtho2D(0, 1000, 0, 800)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glTranslatef(x, y, 0)
        glColor3f(1, 0.2, 0.4)
        glutSolidSphere(heart_size * 0.4, 8, 8)
        glTranslatef(heart_size * 0.6, 0, 0)
        glutSolidSphere(heart_size * 0.4, 8, 8)
        glBegin(GL_TRIANGLES)
        glVertex2f(-heart_size * 0.3, -heart_size * 0.2)
        glVertex2f(heart_size * 0.9, -heart_size * 0.2)
        glVertex2f(heart_size * 0.3, -heart_size)
        glEnd()
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)



def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    speed = 0.5 if slow_motion else 1.0
    gluPerspective(fovY * speed, 1000 / 800, 1, 5000)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    x, y, z = camera_pos
    gluLookAt(x, y, z, 0, 0, 0, 0, 1, 0)


def keyboardListener(key, x, y):
    global slow_motion, game_won, game_over

    key_str = key.decode("utf-8") if isinstance(key, bytes) else str(key)
    key_str = key_str.lower()

    if game_won or game_over:
        if key_str == "r":
            generate_maze()
        return

    if key_str == "q":
        use_ability("sprint")
    elif key_str == "e":
        use_ability("invis")
    elif key_str == "f":
        use_ability("shield")
    elif key_str == " ":
        slow_motion = not slow_motion

    nx, nz = player_pos
    if key_str == "w":
        nz -= 1
    elif key_str == "s":
        nz += 1
    elif key_str == "a":
        nx -= 1
    elif key_str == "d":
        nx += 1

    if can_move(nx, nz):
        player_pos[:] = [nx, nz]
        collect_coins(nx, nz)
        check_puzzles(nx, nz)
        check_enemy_collision()
        if nx == END_POS[0] and nz == END_POS[1]:
            game_won = True

    glutPostRedisplay()


def specialKeyListener(key, x, y):
    global camera_pos
    cx, cy, cz = camera_pos
    if key == GLUT_KEY_LEFT:
        cx -= 20
    elif key == GLUT_KEY_RIGHT:
        cx += 20
    elif key == GLUT_KEY_UP:
        cz -= 20
    elif key == GLUT_KEY_DOWN:
        cz += 20
    camera_pos = (cx, cy, cz)
    glutPostRedisplay()


def correct_player_position():
    px = (player_pos[0] - MAZE_SIZE / 2) * CELL_SIZE
    pz = (player_pos[1] - MAZE_SIZE / 2) * CELL_SIZE
    if sphere_cube_collision(px, pz):
        for dx in [-1, 0, 1]:
            for dz in [-1, 0, 1]:
                if dx == 0 and dz == 0:
                    continue
                nx, nz = player_pos[0] + dx, player_pos[1] + dz
                if can_move(nx, nz):
                    player_pos[:] = [nx, nz]
                    return


def idle():
    correct_player_position()
    update_dynamic_maze()
    update_abilities()

    px, pz = player_pos[0], player_pos[1]
    for enemy in enemies:
        enemy.update(px, pz)

    check_enemy_collision()
    glutPostRedisplay()



def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glViewport(0, 0, 1000, 800)
    glEnable(GL_DEPTH_TEST)

    setupCamera()

    glColor3f(0.1, 0.1, 0.1)
    glBegin(GL_QUADS)
    glVertex3f(-GRID_LENGTH, 0, GRID_LENGTH)
    glVertex3f(GRID_LENGTH, 0, GRID_LENGTH)
    glVertex3f(GRID_LENGTH, 0, -GRID_LENGTH)
    glVertex3f(-GRID_LENGTH, 0, -GRID_LENGTH)
    glEnd()

    draw_maze()
    draw_enemies()
    draw_coins()
    draw_player()
    draw_lives()

    draw_text(10, 770, f"Score: {score} Coins: {coins_collected}/{total_coins}")
    draw_text(10, 740, f"HP: {player_health} Lives: {player_lives} Time: {game_time // 60}")
    draw_text(10, 710, f"S:{abilities['sprint']} I:{abilities['invis']} H:{abilities['shield']}")
    draw_text(10, 680, "Q=Sprint E=Invis F=Shield SPACE=Slow-mo R=Restart")

    if game_won:
        draw_text(300, 400, f"YOU WIN! FINAL SCORE: {score}")
    elif game_over:
        draw_text(300, 400, "GAME OVER! R=Restart")

    glutSwapBuffers()


def main():
    generate_maze()
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(1000, 800)
    glutInitWindowPosition(50, 50)
    glutCreateWindow(b"3D MAZE ")
    glClearColor(0, 0, 0, 1)
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutIdleFunc(idle)
    glutMainLoop()


if __name__ == "__main__":
    main()
