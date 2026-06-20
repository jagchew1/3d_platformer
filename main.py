from math import cos, sin

from ursina import (
    AmbientLight,
    Audio,
    Button,
    DirectionalLight,
    Entity,
    Text,
    Ursina,
    Vec2,
    Vec3,
    camera,
    color,
    distance_xz,
    held_keys,
    load_texture,
    mouse,
    raycast,
    scene,
    time,
    window,
)
from ursina.shaders import unlit_shader


app = Ursina()

# Ursina 8 stores color.rgb values as 0-1 floats. These wrappers let the
# rest of the file use familiar 0-255 palette values without washing to white.
_ursina_rgb = color.rgb
_ursina_rgba = color.rgba


def rgb(r, g, b):
    return _ursina_rgb(r / 255, g / 255, b / 255)


def rgba(r, g, b, a):
    return _ursina_rgba(r / 255, g / 255, b / 255, a / 255)


color.rgb = rgb
color.rgba = rgba

window.title = "Skybound Steps"
window.borderless = False
window.exit_button.visible = False
window.fps_counter.enabled = True
window.color = color.rgb(105, 180, 235)
mouse.locked = True

GRAVITY = 36
MOVE_SPEED = 8.5
SPRINT_SPEED = 11.5
AIR_CONTROL = 0.55
JUMP_SPEED = 14.5
PLAYER_HEIGHT = 1.8
PLAYER_RADIUS = 0.42
CAMERA_DISTANCE = 10.5
CAMERA_HEIGHT = 5.2
MOUSE_SENSITIVITY = 115
FALL_LIMIT = -22
MUSIC_FADE_SPEED = 0.45
MUSIC_SWITCH_X = 45

spawn_point = Vec3(-18, 4.5, -3)
checkpoint = Vec3(spawn_point)
velocity = Vec3(0, 0, 0)
camera_yaw = 0
camera_pitch = 20
score = 0
won = False
paused = False

platforms = []
coins = []
hazards = []
checkpoints = []
moving_platforms = []
scenic_entities = []
music_tracks = []
active_music_index = 0


def to_vec3(value):
    if isinstance(value, Vec3):
        return Vec3(value)
    return Vec3(*value)


def texture(path):
    return load_texture(path, filtering="mipmap")


grass_texture = texture("assets/grass_texture.png")
rock_texture = texture("assets/rock_texture.png")
wood_texture = texture("assets/wood_texture.png")
bark_texture = texture("assets/bark_texture.png")
sky_texture = texture("assets/sky_panorama.png")
explorer_idle_texture = texture("assets/sprites/explorer_idle_back.png")
explorer_walk_textures = [
    texture("assets/sprites/explorer_walk_back_000.png"),
    texture("assets/sprites/explorer_walk_back_001.png"),
]
explorer_jump_texture = texture("assets/sprites/explorer_jump_back.png")
flare_textures = [texture(f"assets/sprites/flare_{index:03}.png") for index in range(6)]


def make_entity(
    model,
    position,
    scale,
    tint,
    collider=None,
    rotation=(0, 0, 0),
    parent=None,
    texture_asset=None,
    texture_scale=(1, 1),
    shader=None,
):
    kwargs = {
        "parent": scene if parent is None else parent,
        "model": model,
        "position": position,
        "scale": scale,
        "color": tint,
        "collider": collider,
        "rotation": rotation,
    }
    if texture_asset is not None:
        kwargs["texture"] = texture_asset
        kwargs["texture_scale"] = texture_scale
    if shader is not None:
        kwargs["shader"] = shader

    return Entity(
        **kwargs
    )


def make_platform(
    position,
    scale,
    top_color,
    side_color=None,
    surface_texture=grass_texture,
    side_texture=rock_texture,
):
    position = to_vec3(position)
    texture_repeats = (max(1, scale[0] / 3), max(1, scale[2] / 3))
    platform = make_entity(
        "cube",
        position,
        scale,
        top_color,
        "box",
        texture_asset=surface_texture,
        texture_scale=texture_repeats,
    )
    platforms.append(platform)

    if side_color:
        skirt = make_entity(
            "cube",
            position + Vec3(0, -scale[1] * 0.62, 0),
            (scale[0] * 0.92, scale[1] * 1.35, scale[2] * 0.92),
            side_color,
            texture_asset=side_texture,
            texture_scale=(max(1, scale[0] / 4), max(1, scale[1] * 1.5)),
        )
        scenic_entities.append(skirt)

    return platform


def make_coin(position):
    coin = make_entity("sphere", position, 0.42, color.rgb(255, 221, 75), "sphere")
    coin.base_y = position.y
    coin.glow = make_entity(
        "sphere",
        (0, 0, 0),
        0.7,
        color.rgba(255, 230, 130, 55),
        parent=coin,
    )
    coins.append(coin)
    return coin


def make_hazard(position, scale):
    hazard = make_entity("cube", position, scale, color.rgb(224, 63, 74), "box")
    hazard.visible = False
    hazard.visual = Entity(
        parent=scene,
        model="quad",
        texture=flare_textures[0],
        position=to_vec3(position) + Vec3(0, scale[1] * 1.35, 0),
        scale=(scale[0] * 1.6, max(scale[2] * 2.8, 3.6)),
        color=color.white,
        shader=unlit_shader,
        double_sided=True,
    )
    hazard.visual.base_y = hazard.visual.y
    hazard.visual.phase = len(hazards) * 0.47
    hazards.append(hazard)
    return hazard


def make_checkpoint(position):
    position = to_vec3(position)
    base = make_entity("cube", position, (1.3, 0.18, 1.3), color.rgb(86, 202, 190), "box")
    pillar = make_entity(
        "cube",
        position + Vec3(0, 0.9, 0),
        (0.18, 1.8, 0.18),
        color.rgb(240, 255, 245),
    )
    ring = make_entity(
        "sphere",
        position + Vec3(0, 1.8, 0),
        (0.95, 0.14, 0.95),
        color.rgba(103, 232, 220, 135),
    )
    ring.base_y = ring.y
    base.pillar = pillar
    base.ring = ring
    base.active = False
    checkpoints.append(base)
    return base


def make_tree(position, height=2.8, canopy=1.7):
    position = to_vec3(position)
    trunk = make_entity(
        "cube",
        position + Vec3(0, height * 0.3, 0),
        (0.42, height * 0.6, 0.42),
        color.rgb(185, 170, 145),
        texture_asset=bark_texture,
        texture_scale=(1, max(1, height / 2)),
    )
    top = make_entity(
        "sphere",
        position + Vec3(0, height, 0),
        (canopy, canopy * 0.85, canopy),
        color.rgb(120, 170, 105),
        texture_asset=grass_texture,
        texture_scale=(2, 2),
    )
    scenic_entities.extend([trunk, top])


def make_crystal(position, scale=1, tint=color.rgb(117, 218, 255)):
    shard = make_entity(
        "cube",
        position,
        (0.45 * scale, 1.7 * scale, 0.45 * scale),
        tint,
        rotation=(0, 45, 0),
    )
    shard.base_y = position.y
    scenic_entities.append(shard)
    return shard


def make_bridge(start, count, step):
    for index in range(count):
        offset = Vec3(step[0] * index, step[1] * index, step[2] * index)
        make_platform(
            Vec3(*start) + offset,
            (2.2, 0.42, 2.2),
            color.rgb(210, 198, 178),
            color.rgb(150, 132, 104),
            surface_texture=wood_texture,
            side_texture=wood_texture,
        )


AmbientLight(color=color.rgb(132, 152, 172))
DirectionalLight(rotation=(48, -38, 28), color=color.rgb(255, 242, 216))
DirectionalLight(rotation=(-20, 140, 0), color=color.rgba(105, 152, 235, 90))

sky_backdrop = Entity(
    parent=camera,
    model="quad",
    texture=sky_texture,
    position=(0, 6, 82),
    scale=(132, 59),
    color=color.white,
    shader=unlit_shader,
    double_sided=True,
)

water = make_entity(
    "cube",
    (18, -18, 0),
    (130, 1, 105),
    color.rgba(49, 132, 191, 180),
)

# The route is built as a chain of distinct little places, so exploring feels authored.
make_platform((-18, 0, -3), (15, 1.1, 13), color.rgb(75, 170, 113), color.rgb(88, 98, 83))
make_platform((-8, 1.7, -1), (7, 0.8, 5.5), color.rgb(92, 172, 147), color.rgb(76, 94, 101))
make_bridge((-1, 2.4, 0), 4, (2.8, 0.25, 0.75))
make_platform((12, 4.1, 4), (10, 0.9, 7), color.rgb(91, 146, 204), color.rgb(66, 72, 116))
make_platform((20, 5.5, -4), (5.5, 0.75, 5.5), color.rgb(151, 132, 214), color.rgb(86, 71, 132))
make_platform((29, 7.2, -8), (9, 0.9, 6), color.rgb(78, 170, 158), color.rgb(61, 97, 106))
make_bridge((36, 8.2, -4.5), 5, (2.4, 0.35, 1.0))
make_platform((49, 10.4, 1.5), (11, 1, 8), color.rgb(96, 178, 104), color.rgb(86, 103, 71))
make_platform((60, 12.3, -5), (7, 0.85, 5.5), color.rgb(225, 178, 92), color.rgb(130, 91, 58))
make_platform((70, 14.6, -2), (12, 1.1, 9), color.rgb(88, 164, 196), color.rgb(57, 80, 111))

lift = make_platform(
    (41, 8.5, 4.8),
    (4.2, 0.62, 3.3),
    color.rgb(220, 196, 155),
    color.rgb(150, 120, 84),
    surface_texture=wood_texture,
    side_texture=wood_texture,
)
lift.start = Vec3(lift.position)
lift.motion = Vec3(0, 2.1, -6.2)
lift.speed = 1.0
moving_platforms.append(lift)
lift.delta = Vec3(0, 0, 0)

ferry = make_platform(
    (57, 11.2, 2.8),
    (4.6, 0.62, 3.3),
    color.rgb(220, 196, 155),
    color.rgb(150, 120, 84),
    surface_texture=wood_texture,
    side_texture=wood_texture,
)
ferry.start = Vec3(ferry.position)
ferry.motion = Vec3(5.8, 0, -4.4)
ferry.speed = 1.25
moving_platforms.append(ferry)
ferry.delta = Vec3(0, 0, 0)

for tree_position in [(-22, 0.7, -7), (-15, 0.7, 2), (-10, 2.4, -3), (10, 4.8, 7), (47, 11.1, -1), (53, 11.1, 4)]:
    make_tree(Vec3(*tree_position))

for crystal_position, crystal_color in [
    ((13, 5.0, 0), color.rgb(104, 218, 255)),
    ((18, 6.2, -6.4), color.rgb(186, 128, 255)),
    ((30, 8.1, -10.5), color.rgb(117, 245, 203)),
    ((66, 15.4, 1.5), color.rgb(255, 216, 116)),
]:
    make_crystal(Vec3(*crystal_position), 1.0, crystal_color)

for hazard_position, hazard_scale in [
    ((-13, 0.78, -7.2), (2.2, 0.3, 1.5)),
    ((11.5, 4.78, 6.8), (2.1, 0.3, 1.7)),
    ((29, 7.86, -8), (2.2, 0.3, 2.2)),
    ((50.8, 11.08, 3.7), (2.0, 0.3, 2.0)),
    ((69.5, 15.28, -5.3), (2.6, 0.3, 1.6)),
]:
    make_hazard(hazard_position, hazard_scale)

for coin_position in [
    (-20, 1.4, -3),
    (-13.4, 1.5, 0.8),
    (-7.8, 2.8, -1),
    (1.0, 4.0, 0.5),
    (9.5, 5.5, 3.8),
    (14.2, 5.5, 6.4),
    (20.0, 6.8, -4),
    (28.2, 8.5, -8),
    (35.5, 9.6, -4.2),
    (41.0, 10.9, -1.2),
    (49.5, 11.8, 1.5),
    (57.0, 13.2, 2.8),
    (60.0, 13.7, -5),
    (70.0, 16.0, -2),
]:
    make_coin(Vec3(*coin_position))

make_checkpoint((-8, 2.3, -1))
make_checkpoint((29, 7.85, -8))
make_checkpoint((49, 11.05, 1.5))

goal = make_entity(
    "cube",
    (73.5, 16.6, -2),
    (0.42, 4.3, 0.42),
    color.rgb(244, 252, 255),
    "box",
)
flag = make_entity(
    "cube",
    (1.1, 0.7, 0),
    (2.25, 1.2, 0.08),
    color.rgb(76, 226, 182),
    parent=goal,
)
beacon = make_entity(
    "sphere",
    (0, 2.55, 0),
    1.0,
    color.rgba(125, 238, 220, 110),
    parent=goal,
)

player = make_entity(
    "cube",
    spawn_point,
    (PLAYER_RADIUS * 2, PLAYER_HEIGHT, PLAYER_RADIUS * 2),
    color.rgb(255, 145, 75),
    "box",
)
face = make_entity("cube", (0, 0.18, -0.46), (0.42, 0.25, 0.04), color.rgb(255, 234, 168), parent=player)
player.visible = False
face.enabled = False

player_sprite = Entity(
    parent=scene,
    model="quad",
    texture=explorer_idle_texture,
    position=player.position + Vec3(0, 0.25, 0),
    scale=(1.35, 2.45),
    color=color.white,
    shader=unlit_shader,
    double_sided=True,
)

shadow = make_entity("circle", (0, 0, 0), 1.2, color.rgba(0, 0, 0, 70), rotation=(90, 0, 0))

score_text = Text(
    text="Shards: 0 / 14",
    position=(-0.86, 0.45),
    origin=(-0.5, 0),
    scale=1.35,
    color=color.rgb(28, 45, 58),
)
location_text = Text(
    text="Skymeadow",
    position=(-0.86, 0.39),
    origin=(-0.5, 0),
    scale=1.0,
    color=color.rgb(33, 78, 92),
)
message_text = Text(text="", position=(0, 0.31), origin=(0, 0), scale=1.65, color=color.rgb(26, 44, 58))
hint_text = Text(
    text="Mouse look  WASD move  Space jump  Shift sprint  R restart",
    position=(0, -0.46),
    origin=(0, 0),
    scale=0.95,
    color=color.rgb(38, 62, 76),
)

restart_button = Button(
    text="Restart",
    position=(0.78, 0.43),
    scale=(0.14, 0.055),
    color=color.rgba(35, 40, 48, 210),
    text_color=color.white,
)


def start_music():
    global music_tracks

    music_tracks = [
        Audio("music/track1.mp3", loop=True, autoplay=True, volume=0.55),
        Audio("music/track2.mp3", loop=True, autoplay=True, volume=0),
    ]


def update_music():
    global active_music_index

    target_index = 1 if player.x >= MUSIC_SWITCH_X else 0
    active_music_index = target_index

    for index, track in enumerate(music_tracks):
        target_volume = 0.55 if index == active_music_index else 0
        track.volume += (target_volume - track.volume) * min(1, MUSIC_FADE_SPEED * time.dt)


def reset_game():
    global checkpoint, score, velocity, won

    checkpoint = Vec3(spawn_point)
    score = 0
    velocity = Vec3(0, 0, 0)
    won = False
    player.position = Vec3(spawn_point)
    player.color = color.rgb(255, 145, 75)
    message_text.text = ""
    score_text.text = f"Shards: {score} / {len(coins)}"

    for coin in coins:
        coin.enabled = True
    for marker in checkpoints:
        marker.active = False
        marker.color = color.rgb(86, 202, 190)
        marker.ring.color = color.rgb(103, 232, 220)


restart_button.on_click = reset_game


def ground_check():
    start = player.world_position + Vec3(0, 0.18, 0)
    return raycast(
        start,
        Vec3(0, -1, 0),
        distance=(PLAYER_HEIGHT / 2) + 0.38,
        ignore=[player],
    )


def movement_vectors():
    yaw = camera_yaw * 0.01745329252
    forward = Vec3(sin(yaw), 0, cos(yaw)).normalized()
    right = Vec3(forward.z, 0, -forward.x).normalized()
    return forward, right


def move_player(move_direction, grounded):
    global velocity

    support = ground_check()
    if support.hit and hasattr(support.entity, "delta") and velocity.y <= 0:
        player.position += support.entity.delta

    speed = SPRINT_SPEED if held_keys["shift"] else MOVE_SPEED
    control = 1 if grounded else AIR_CONTROL
    target_x = move_direction.x * speed * control
    target_z = move_direction.z * speed * control

    velocity.x += (target_x - velocity.x) * min(1, 12 * time.dt)
    velocity.z += (target_z - velocity.z) * min(1, 12 * time.dt)

    if grounded and held_keys["space"]:
        velocity.y = JUMP_SPEED

    velocity.y -= GRAVITY * time.dt
    player.position += velocity * time.dt

    hit = ground_check()
    if hit.hit and velocity.y <= 0:
        player.y = hit.world_point.y + (PLAYER_HEIGHT / 2)
        velocity.y = 0

    if move_direction.length() > 0.05:
        player.look_at(player.position + move_direction)
        player.rotation_x = 0
        player.rotation_z = 0


def face_camera(entity):
    entity.look_at(camera.position)
    entity.rotation_z = 0


def update_player_sprite(move_direction, grounded):
    player_sprite.position = player.position + Vec3(0, 0.22, 0)

    if not grounded:
        player_sprite.texture = explorer_jump_texture
        player_sprite.scale = (1.65, 2.35)
    elif move_direction.length() > 0.05:
        frame = int(time.time() * 8) % len(explorer_walk_textures)
        player_sprite.texture = explorer_walk_textures[frame]
        player_sprite.scale = (1.45, 2.42 + sin(time.time() * 16) * 0.04)
    else:
        player_sprite.texture = explorer_idle_texture
        player_sprite.scale = (1.35, 2.45 + sin(time.time() * 2.5) * 0.025)

    face_camera(player_sprite)


def update_camera():
    forward, _ = movement_vectors()
    target = player.position + Vec3(0, 1.45, 0)
    pitch_lift = (camera_pitch - 20) * 0.09
    desired = target - (forward * CAMERA_DISTANCE) + Vec3(0, CAMERA_HEIGHT + pitch_lift, 0)
    camera.position = camera.position + (desired - camera.position) * min(1, 6.5 * time.dt)
    camera.look_at(target)
    camera.rotation_x += camera_pitch * 0.2
    camera.rotation_z = 0


def update_backdrop():
    sky_backdrop.texture_offset = (
        (camera_yaw * 0.0012) + (player.x * 0.0014),
        (camera_pitch * 0.0015) + (player.y * 0.002) - (player.z * 0.0007),
    )


def animate_world():
    for platform in moving_platforms:
        previous_position = Vec3(platform.position)
        phase = sin(time.time() * platform.speed)
        platform.position = platform.start + platform.motion * ((phase + 1) * 0.5)
        platform.delta = platform.position - previous_position

    for coin in coins:
        if coin.enabled:
            coin.rotation_y += 140 * time.dt
            coin.y = coin.base_y + sin(time.time() * 3 + coin.x) * 0.14

    for marker in checkpoints:
        marker.ring.rotation_y += 65 * time.dt
        marker.ring.y = marker.ring.base_y + sin(time.time() * 2 + marker.x) * 0.08

    for index, hazard in enumerate(hazards):
        frame = int((time.time() * 12) + index) % len(flare_textures)
        hazard.visual.texture = flare_textures[frame]
        hazard.visual.y = hazard.visual.base_y + sin(time.time() * 5 + hazard.visual.phase) * 0.08
        hazard.visual.scale_x = hazard.scale_x * (1.45 + sin(time.time() * 7 + index) * 0.12)
        face_camera(hazard.visual)

    for entity in scenic_entities:
        if hasattr(entity, "base_y"):
            entity.rotation_y += 18 * time.dt
            entity.y = entity.base_y + sin(time.time() * 1.8 + entity.x) * 0.06

    water.y = -18 + sin(time.time() * 0.65) * 0.18
    flag.rotation_y = sin(time.time() * 4) * 7
    beacon.scale = 1.0 + sin(time.time() * 3.5) * 0.08


def collect_coins():
    global score

    for coin in coins:
        if coin.enabled and distance_xz(player.position, coin.position) < 0.85:
            if abs(player.y - coin.y) < 1.8:
                coin.enabled = False
                score += 1
                score_text.text = f"Shards: {score} / {len(coins)}"
                message_text.text = "Shard collected"


def update_checkpoints():
    global checkpoint

    for marker in checkpoints:
        if distance_xz(player.position, marker.position) < 1.35 and abs(player.y - marker.y) < 2.2:
            checkpoint = marker.position + Vec3(0, 2.4, 0)
            marker.active = True
            marker.color = color.rgb(232, 250, 188)
            marker.ring.color = color.rgba(255, 245, 148, 170)
            message_text.text = "Checkpoint lit"


def update_location_label():
    if player.x < -4:
        location_text.text = "Skymeadow"
    elif player.x < 24:
        location_text.text = "Blueglass Ruins"
    elif player.x < 45:
        location_text.text = "Windway"
    elif player.x < 62:
        location_text.text = "Sunspoke Garden"
    else:
        location_text.text = "Beacon Summit"


def hazard_check():
    for hazard in hazards:
        if player.intersects(hazard).hit:
            message_text.text = "You touched a flare. Back to the last checkpoint."
            reset_position()
            return

    if player.y < FALL_LIMIT:
        message_text.text = "The wind catches you."
        reset_position()


def reset_position():
    global velocity

    velocity = Vec3(0, 0, 0)
    player.position = Vec3(checkpoint)


def win_check():
    global won

    if not won and player.intersects(goal).hit:
        won = True
        player.color = color.rgb(119, 255, 159)
        message_text.text = f"Beacon reached with {score} / {len(coins)} shards"


def input(key):
    global paused

    if key == "r":
        reset_game()
    elif key == "escape":
        paused = not paused
        mouse.locked = not paused
        message_text.text = "Paused" if paused else ""


def update():
    global camera_pitch, camera_yaw

    if paused:
        return

    camera_yaw += mouse.velocity[0] * MOUSE_SENSITIVITY
    camera_pitch -= mouse.velocity[1] * MOUSE_SENSITIVITY
    camera_pitch = max(-8, min(48, camera_pitch))

    animate_world()

    forward, right = movement_vectors()
    raw_input = Vec2(
        held_keys["d"] - held_keys["a"],
        held_keys["w"] - held_keys["s"],
    )
    move_direction = (right * raw_input.x + forward * raw_input.y).normalized()

    grounded = ground_check().hit
    if not won:
        move_player(move_direction, grounded)
    update_player_sprite(move_direction, grounded)

    collect_coins()
    update_checkpoints()
    update_location_label()
    update_music()
    hazard_check()
    win_check()

    ground_hit = ground_check()
    shadow.enabled = ground_hit.hit
    if ground_hit.hit:
        shadow.position = ground_hit.world_point + Vec3(0, 0.045, 0)
        shadow.scale = max(0.28, 1.25 - abs(player.y - ground_hit.world_point.y) * 0.08)

    update_camera()
    update_backdrop()


camera.position = spawn_point - (movement_vectors()[0] * CAMERA_DISTANCE) + Vec3(0, CAMERA_HEIGHT, 0)
camera.look_at(spawn_point)
camera.rotation_z = 0

reset_game()
start_music()
app.run()
