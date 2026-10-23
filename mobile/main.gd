extends Node

const GRAVITY := 36.0
const MOVE_SPEED := 8.5
const SPRINT_SPEED := 11.5
const JUMP_SPEED := 14.5
const FALL_LIMIT := -22.0
const CAMERA_DISTANCE := 10.5
const CAMERA_HEIGHT := 5.2

var player: CharacterBody3D
var camera: Camera3D
var camera_yaw := 0.0
var camera_pitch := -17.0
var spawn_point := Vector3(-18, 4.5, -3)
var checkpoint := spawn_point
var joystick := Vector2.ZERO
var joystick_touch := -1
var look_touch := -1
var look_last := Vector2.ZERO
var jump_queued := false
var score := 0
var won := false
var coins: Array[Area3D] = []
var hazards: Array[Area3D] = []
var checkpoints: Array[Area3D] = []
var moving_platforms: Array[AnimatableBody3D] = []
var score_label: Label
var location_label: Label
var message_label: Label
var stick_base: Control
var stick_knob: Control
var jump_button: Button
var start_overlay: Control

var platform_data = [
	[Vector3(-18,0,-3), Vector3(15,1.1,13), Color("4baa71")],
	[Vector3(-8,1.7,-1), Vector3(7,.8,5.5), Color("5cac93")],
	[Vector3(12,4.1,4), Vector3(10,.9,7), Color("5b92cc")],
	[Vector3(20,5.5,-4), Vector3(5.5,.75,5.5), Color("9784d6")],
	[Vector3(29,7.2,-8), Vector3(9,.9,6), Color("4eaa9e")],
	[Vector3(49,10.4,1.5), Vector3(11,1,8), Color("60b268")],
	[Vector3(60,12.3,-5), Vector3(7,.85,5.5), Color("e1b25c")],
	[Vector3(70,14.6,-2), Vector3(12,1.1,9), Color("58a4c4")],
]

func _ready() -> void:
	build_world()
	build_player()
	build_ui()
	get_viewport().size_changed.connect(layout_touch_controls)

func material(color: Color) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = .85
	return mat

func add_box(pos: Vector3, size: Vector3, tint: Color, collision := true) -> Node3D:
	var root: Node3D
	if collision:
		root = StaticBody3D.new()
	else:
		root = Node3D.new()
	root.position = pos
	var mesh := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = size
	mesh.mesh = box
	mesh.material_override = material(tint)
	root.add_child(mesh)
	if collision:
		var shape := CollisionShape3D.new()
		var box_shape := BoxShape3D.new()
		box_shape.size = size
		shape.shape = box_shape
		root.add_child(shape)
	add_child(root)
	return root

func add_platform(pos: Vector3, size: Vector3, tint: Color) -> void:
	add_box(pos, size, tint)
	add_box(pos + Vector3(0, -size.y * .85, 0), Vector3(size.x*.92,size.y*.7,size.z*.92), tint.darkened(.35), false)

func build_world() -> void:
	var environment := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("70b8e8")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("b9cae1")
	env.ambient_light_energy = .7
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	environment.environment = env
	add_child(environment)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-48,-38,0)
	sun.light_color = Color("fff2d8")
	sun.light_energy = 1.15
	sun.shadow_enabled = true
	add_child(sun)
	for data in platform_data:
		add_platform(data[0], data[1], data[2])
	for i in 4:
		add_platform(Vector3(-1,2.4,0)+Vector3(2.8,.25,.75)*i, Vector3(2.2,.42,2.2), Color("d2c6b2"))
	for i in 5:
		add_platform(Vector3(36,8.2,-4.5)+Vector3(2.4,.35,1)*i, Vector3(2.2,.42,2.2), Color("d2c6b2"))
	add_box(Vector3(18,-18,0), Vector3(130,1,105), Color("3184bf"), false)
	for p in [Vector3(-20,1.4,-3),Vector3(-13.4,1.5,.8),Vector3(-7.8,2.8,-1),Vector3(1,4,.5),Vector3(9.5,5.5,3.8),Vector3(14.2,5.5,6.4),Vector3(20,6.8,-4),Vector3(28.2,8.5,-8),Vector3(35.5,9.6,-4.2),Vector3(41,10.9,-1.2),Vector3(49.5,11.8,1.5),Vector3(57,13.2,2.8),Vector3(60,13.7,-5),Vector3(70,16,-2)]:
		add_coin(p)
	for entry in [[Vector3(-13,.78,-7.2),Vector3(2.2,.3,1.5)],[Vector3(11.5,4.78,6.8),Vector3(2.1,.3,1.7)],[Vector3(29,7.86,-8),Vector3(2.2,.3,2.2)],[Vector3(50.8,11.08,3.7),Vector3(2,.3,2)],[Vector3(69.5,15.28,-5.3),Vector3(2.6,.3,1.6)]]:
		add_hazard(entry[0],entry[1])
	for p in [Vector3(-8,2.3,-1),Vector3(29,7.85,-8),Vector3(49,11.05,1.5)]:
		add_checkpoint(p)
	add_box(Vector3(73.5,16.6,-2), Vector3(.42,4.3,.42), Color.WHITE)
	add_box(Vector3(74.6,17.3,-2), Vector3(2.25,1.2,.08), Color("4ce2b6"), false)

func add_coin(pos: Vector3) -> void:
	var area := Area3D.new()
	area.position = pos
	var mesh := MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = .42
	sphere.height = .84
	mesh.mesh = sphere
	mesh.material_override = material(Color("ffdd4b"))
	area.add_child(mesh)
	var shape := CollisionShape3D.new()
	var sphere_shape := SphereShape3D.new()
	sphere_shape.radius = .7
	shape.shape = sphere_shape
	area.add_child(shape)
	area.body_entered.connect(func(body): collect_coin(area, body))
	add_child(area)
	coins.append(area)

func add_hazard(pos: Vector3, size: Vector3) -> void:
	var area := Area3D.new()
	area.position = pos
	var mesh := MeshInstance3D.new()
	var box := BoxMesh.new(); box.size = Vector3(size.x,size.y+.5,size.z)
	mesh.mesh = box; mesh.material_override = material(Color("e03f4a"))
	area.add_child(mesh)
	var shape := CollisionShape3D.new()
	var box_shape := BoxShape3D.new(); box_shape.size = size
	shape.shape = box_shape; area.add_child(shape)
	area.body_entered.connect(func(body): hit_hazard(body))
	add_child(area); hazards.append(area)

func add_checkpoint(pos: Vector3) -> void:
	var area := Area3D.new(); area.position = pos
	var mesh := MeshInstance3D.new(); var cylinder := CylinderMesh.new()
	cylinder.top_radius=.7; cylinder.bottom_radius=.7; cylinder.height=.18
	mesh.mesh=cylinder; mesh.material_override=material(Color("56cabe")); area.add_child(mesh)
	var shape := CollisionShape3D.new(); var sphere := SphereShape3D.new(); sphere.radius=1.35
	shape.shape=sphere; area.add_child(shape)
	area.body_entered.connect(func(body): activate_checkpoint(area,body))
	add_child(area); checkpoints.append(area)

func build_player() -> void:
	player = CharacterBody3D.new()
	player.position = spawn_point
	var shape := CollisionShape3D.new(); var capsule := CapsuleShape3D.new()
	capsule.radius=.42; capsule.height=1.8; shape.shape=capsule; player.add_child(shape)
	var sprite := Sprite3D.new()
	sprite.texture=load("res://assets/sprites/explorer_idle_back.png")
	sprite.pixel_size=.0095; sprite.position.y=.15; sprite.billboard=BaseMaterial3D.BILLBOARD_ENABLED
	player.add_child(sprite); add_child(player)
	camera=Camera3D.new(); camera.current=true; add_child(camera)

func build_ui() -> void:
	var layer := CanvasLayer.new(); add_child(layer)
	score_label = label("Shards: 0 / 14", 28, Vector2(28,24)); layer.add_child(score_label)
	location_label = label("Skymeadow", 20, Vector2(30,58)); layer.add_child(location_label)
	message_label = label("", 28, Vector2.ZERO); message_label.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER
	message_label.set_anchors_preset(Control.PRESET_CENTER_TOP); message_label.position=Vector2(-260,28); message_label.size=Vector2(520,50); layer.add_child(message_label)
	stick_base = touch_circle(Color(1,1,1,.18)); stick_base.size=Vector2(150,150); layer.add_child(stick_base)
	stick_knob = touch_circle(Color(1,1,1,.5)); stick_knob.size=Vector2(68,68); layer.add_child(stick_knob)
	jump_button=Button.new(); jump_button.text="JUMP"; jump_button.add_theme_font_size_override("font_size",24)
	jump_button.modulate=Color(1,1,1,.82); jump_button.button_down.connect(func(): jump_queued=true)
	jump_button.size=Vector2(130,130); layer.add_child(jump_button)
	var restart:=Button.new(); restart.text="↻"; restart.size=Vector2(58,48); restart.set_anchors_preset(Control.PRESET_TOP_RIGHT); restart.position=Vector2(-78,22); restart.pressed.connect(reset_game); layer.add_child(restart)
	start_overlay=ColorRect.new(); start_overlay.color=Color(0.03,.08,.13,.92); start_overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT); layer.add_child(start_overlay)
	var start:=Button.new(); start.text="TAP TO PLAY\nSkybound Steps"; start.add_theme_font_size_override("font_size",32); start.set_anchors_preset(Control.PRESET_CENTER); start.position=Vector2(-180,-70); start.size=Vector2(360,140); start.pressed.connect(begin_game); start_overlay.add_child(start)
	layout_touch_controls()

func label(text:String,font_size:int,pos:Vector2)->Label:
	var item:=Label.new(); item.text=text; item.position=pos; item.add_theme_font_size_override("font_size",font_size); item.add_theme_color_override("font_color",Color("183347")); return item

func touch_circle(tint:Color)->Control:
	var panel:=Panel.new(); var style:=StyleBoxFlat.new(); style.bg_color=tint; style.corner_radius_top_left=100; style.corner_radius_top_right=100; style.corner_radius_bottom_left=100; style.corner_radius_bottom_right=100; panel.add_theme_stylebox_override("panel",style); panel.mouse_filter=Control.MOUSE_FILTER_IGNORE; return panel

func layout_touch_controls() -> void:
	if not stick_base: return
	var viewport:=get_viewport().get_visible_rect().size
	stick_base.position=Vector2(34,viewport.y-184)
	stick_knob.position=stick_base.position+Vector2(41,41)
	jump_button.position=Vector2(viewport.x-174,viewport.y-164)

func begin_game()->void:
	start_overlay.hide()
	var music:=AudioStreamPlayer.new(); music.stream=load("res://music/track1.mp3"); music.volume_db=-7; music.finished.connect(music.play); add_child(music); music.play()

func _unhandled_input(event:InputEvent)->void:
	if start_overlay and start_overlay.visible: return
	var width:=get_viewport().get_visible_rect().size.x
	if event is InputEventScreenTouch:
		if event.pressed and event.position.x < width*.45 and joystick_touch < 0: joystick_touch=event.index; update_stick(event.position)
		elif event.pressed and event.position.x >= width*.45 and look_touch < 0: look_touch=event.index; look_last=event.position
		elif not event.pressed and event.index==joystick_touch: joystick_touch=-1; joystick=Vector2.ZERO; center_stick()
		elif not event.pressed and event.index==look_touch: look_touch=-1
	elif event is InputEventScreenDrag:
		if event.index==joystick_touch: update_stick(event.position)
		elif event.index==look_touch:
			var drag_delta: Vector2 = event.position-look_last; look_last=event.position; camera_yaw-=drag_delta.x*.18; camera_pitch=clamp(camera_pitch-drag_delta.y*.14,-45.0,8.0)

func update_stick(pos:Vector2)->void:
	var center:=stick_base.position+stick_base.size*.5
	var delta:Vector2=(pos-center).limit_length(62)
	joystick=delta/62.0
	stick_knob.position=center+delta-stick_knob.size*.5

func center_stick()->void: stick_knob.position=stick_base.position+(stick_base.size-stick_knob.size)*.5

func _physics_process(delta:float)->void:
	if not player or (start_overlay and start_overlay.visible): return
	if Input.is_action_just_pressed("restart"): reset_game()
	var keyboard:=Input.get_vector("ui_left","ui_right","ui_up","ui_down")
	var input_vec:=joystick if joystick.length()>.05 else keyboard
	var yaw:=deg_to_rad(camera_yaw)
	var forward:=Vector3(sin(yaw),0,cos(yaw)); var right:=Vector3(forward.z,0,-forward.x)
	var direction:=(right*input_vec.x+forward*-input_vec.y).normalized()
	var speed:=SPRINT_SPEED if input_vec.length()>.88 else MOVE_SPEED
	player.velocity.x=move_toward(player.velocity.x,direction.x*speed,28*delta)
	player.velocity.z=move_toward(player.velocity.z,direction.z*speed,28*delta)
	if player.is_on_floor():
		if jump_queued or Input.is_action_just_pressed("jump"): player.velocity.y=JUMP_SPEED
	else: player.velocity.y-=GRAVITY*delta
	jump_queued=false
	if not won: player.move_and_slide()
	if player.position.y<FALL_LIMIT: respawn("The wind catches you")
	update_camera(delta); update_labels()
	for coin in coins:
		if is_instance_valid(coin): coin.rotate_y(delta*2.5)

func update_camera(delta:float)->void:
	var yaw:=deg_to_rad(camera_yaw); var pitch:=deg_to_rad(camera_pitch)
	var target:=player.global_position+Vector3(0,1.3,0)
	var offset:=Vector3(sin(yaw)*cos(pitch),sin(pitch),cos(yaw)*cos(pitch))*CAMERA_DISTANCE
	var desired:=target-offset+Vector3(0,CAMERA_HEIGHT-2.8,0)
	camera.global_position=camera.global_position.lerp(desired,min(1.0,delta*8)); camera.look_at(target)

func collect_coin(coin:Area3D,body:Node)->void:
	if body!=player: return
	score+=1; coin.queue_free(); message("Shard collected")

func hit_hazard(body:Node)->void:
	if body==player: respawn("Flare! Back to checkpoint")

func activate_checkpoint(marker:Area3D,body:Node)->void:
	if body!=player:return
	checkpoint=marker.position+Vector3(0,2.4,0); message("Checkpoint lit")

func respawn(text:String)->void:
	player.position=checkpoint; player.velocity=Vector3.ZERO; message(text)

func reset_game()->void:
	get_tree().reload_current_scene()

func message(text:String)->void:
	message_label.text=text
	get_tree().create_timer(2).timeout.connect(func(): if message_label.text==text: message_label.text="")

func update_labels()->void:
	score_label.text="Shards: %d / 14"%score
	var x:=player.position.x
	location_label.text="Skymeadow" if x < -4 else ("Blueglass Ruins" if x<24 else ("Windway" if x<45 else ("Sunspoke Garden" if x<62 else "Beacon Summit")))
	if not won and player.position.distance_to(Vector3(73.5,16.6,-2))<2.4:
		won=true; message_label.text="Beacon reached — %d / 14 shards"%score
