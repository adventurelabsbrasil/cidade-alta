## Fatia vertical (#9): carrega o tile gerado pelo pipeline, põe o carro no spawn
## da Av. Borges de Medeiros e mostra o HUD.
## Linha de comando (depois de `--`):
##   --autotest   roda a física sem tela e imprime o resultado
##   --bench      gira a câmera em volta do carro e imprime o FPS
extends Node3D

const DEFAULT_TILE := "fatia"
const BENCH_SECONDS := 20.0

@onready var car: Car = $Car
@onready var camera: Camera3D = $Camera
@onready var hud: Label = $HUD/Info

var spawn := Transform3D.IDENTITY
var meta := {}
var _t := 0.0
var _frames: Array[float] = []
var _mode := ""
var _log: Array[String] = []


func _ready() -> void:
	_setup_input()
	var tile := DEFAULT_TILE
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--tile="):
			tile = arg.trim_prefix("--tile=")
	var world: Node3D = load("res://world/tiles/%s.glb" % tile).instantiate()
	world.name = "Tile"
	add_child(world)
	meta = JSON.parse_string(FileAccess.get_file_as_string("res://world/tiles/%s.json" % tile))
	var s: Dictionary = meta["spawn"]
	spawn = Transform3D(Basis(Vector3.UP, -float(s["heading_from_north"])), Vector3(s["x"], s["y"], s["z"]))
	_add_bounds(float(meta["size_m"]) / 2.0)
	_apply_palette(world)
	reset_car()
	var args := OS.get_cmdline_user_args()
	if "--autotest" in args:
		_mode = "autotest"
	elif "--bench" in args:
		_mode = "bench"
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)


func reset_car() -> void:
	car.global_transform = spawn
	car.linear_velocity = Vector3.ZERO
	car.angular_velocity = Vector3.ZERO
	camera.global_position = spawn.origin + spawn.basis.z * 6.5 + Vector3.UP * 2.4


func _apply_palette(root: Node) -> void:
	# O pipeline grava a cor chapada de cada face no vértice (decisão 001); um
	# material único lê essa cor. Sem textura.
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.vertex_color_is_srgb = true
	mat.roughness = 0.95
	for node in root.find_children("*", "MeshInstance3D", true, false):
		(node as MeshInstance3D).material_override = mat


func _add_bounds(half: float) -> void:
	# Muro invisível na borda do tile: a v0 é uma ilha de 800 m.
	for i in 4:
		var body := StaticBody3D.new()
		var shape := CollisionShape3D.new()
		var box := BoxShape3D.new()
		box.size = Vector3(2 * half, 400, 2)
		shape.shape = box
		body.add_child(shape)
		body.rotation.y = i * PI / 2
		body.position = Vector3(0, 0, -half).rotated(Vector3.UP, i * PI / 2)
		add_child(body)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("reiniciar"):
		reset_car()
	elif event.is_action_pressed("camera"):
		camera.hood = not camera.hood


func _process(delta: float) -> void:
	_t += delta
	if car.global_position.y < -200.0:
		reset_car()
	match _mode:
		"autotest":
			_autotest()
		"bench":
			_bench(delta)
	hud.text = "%d km/h   %d FPS   %s\n[W/S] acelerar/frear  [A/D] direção  [Espaço] freio de mão  [C] câmera  [R] reiniciar" % [
		absi(roundi(car.speed() * 3.6)), Engine.get_frames_per_second(),
		RenderingServer.get_current_rendering_driver_name()]


func _autotest() -> void:
	# Roteiro: assenta, acelera reto, freia, e faz uma curva com freio de mão.
	var phase := ""
	if _t < 2.0:
		phase = "assentar"
		car.autopilot = {"acelerar": 0.0}
	elif _t < 6.0:
		phase = "acelerar"
		car.autopilot = {"acelerar": 1.0}
	elif _t < 9.0:
		phase = "frear"
		car.autopilot = {"frear": 1.0}
	elif _t < 11.0:
		phase = "retomar"
		car.autopilot = {"acelerar": 1.0}
	elif _t < 13.0:
		phase = "drift"
		car.autopilot = {"acelerar": 0.6, "esquerda": 1.0, "freio_de_mao": true}
	else:
		_log.append("FIM")
		print("\n".join(_log))
		get_tree().quit()
		return
	if Engine.get_process_frames() % 30 == 0:
		var up_dot := car.global_basis.y.dot(Vector3.UP)
		var lat := car.linear_velocity.dot(car.global_basis.x)
		_log.append("t=%5.2f %-9s v=%6.1f km/h lat=%5.1f m/s pos=(%.1f, %.1f, %.1f) up=%.2f rodas=%d" % [
			_t, phase, car.speed() * 3.6, lat, car.global_position.x, car.global_position.y,
			car.global_position.z, up_dot, car.wheels.filter(func(w): return w.is_colliding()).size()])


func _bench(delta: float) -> void:
	# Câmera em órbita de 360° ao redor do carro, depois uma passada alta sobre o tile.
	camera.set_physics_process(false)
	var k := _t / BENCH_SECONDS
	var a := k * TAU * 2.0
	var r := 12.0 if k < 0.5 else 180.0
	var h := 3.0 if k < 0.5 else 90.0
	camera.global_position = car.global_position + Vector3(cos(a) * r, h, sin(a) * r)
	camera.look_at(car.global_position, Vector3.UP)
	if _t > 2.0:
		_frames.append(delta)
	# Capturas pra revisão: perto do carro e passada alta.
	for shot in [[5.0, "perto"], [17.0, "alto"]]:
		if _t >= shot[0] and _t - delta < shot[0]:
			var path := ProjectSettings.globalize_path("user://bench_%s_%s.png" % [shot[1], RenderingServer.get_current_rendering_driver_name()])
			get_viewport().get_texture().get_image().save_png(path)
			print("SHOT ", path)
	if _t >= BENCH_SECONDS + 2.0:
		var total := 0.0
		for f in _frames:
			total += f
		_frames.sort()
		var p99: float = _frames[int(_frames.size() * 0.99)]
		print("BENCH driver=%s gpu=%s frames=%d avg_fps=%.1f p99_ms=%.1f" % [
			RenderingServer.get_current_rendering_driver_name(), RenderingServer.get_video_adapter_name(),
			_frames.size(), _frames.size() / total, p99 * 1000.0])
		get_tree().quit()


func _setup_input() -> void:
	var keys := {
		"acelerar": [KEY_W, KEY_UP], "frear": [KEY_S, KEY_DOWN],
		"esquerda": [KEY_A, KEY_LEFT], "direita": [KEY_D, KEY_RIGHT],
		"freio_de_mao": [KEY_SPACE], "camera": [KEY_C], "reiniciar": [KEY_R],
	}
	var axes := {
		"acelerar": [JOY_AXIS_TRIGGER_RIGHT, 1.0], "frear": [JOY_AXIS_TRIGGER_LEFT, 1.0],
		"esquerda": [JOY_AXIS_LEFT_X, -1.0], "direita": [JOY_AXIS_LEFT_X, 1.0],
	}
	var buttons := {"freio_de_mao": JOY_BUTTON_B, "camera": JOY_BUTTON_Y, "reiniciar": JOY_BUTTON_BACK}
	for action in keys:
		if not InputMap.has_action(action):
			InputMap.add_action(action, 0.15)
		for k in keys[action]:
			var e := InputEventKey.new()
			e.physical_keycode = k
			InputMap.action_add_event(action, e)
		if action in axes:
			var j := InputEventJoypadMotion.new()
			j.axis = axes[action][0]
			j.axis_value = axes[action][1]
			InputMap.action_add_event(action, j)
		if action in buttons:
			var b := InputEventJoypadButton.new()
			b.button_index = buttons[action]
			InputMap.action_add_event(action, b)
