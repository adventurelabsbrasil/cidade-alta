## Fatia vertical (#9): carrega o tile gerado pelo pipeline, põe o carro no spawn
## da Av. Borges de Medeiros e mostra o HUD.
## Linha de comando (depois de `--`):
##   --autotest   roda a física sem tela e imprime o resultado
##   --bench      gira a câmera em volta do carro e imprime o FPS
##   --autotest-descoberta  leva o carro a cada ponto do tile e confere cartão e save
##   --save=<caminho>       arquivo de descobertas (padrão user://descobertas.json)
##   --tile=<nome>          tile a carregar (sem isso: o último jogado, ou o anel 1)
## Jogando de verdade (sem modo de teste) abre o menu de início; a posição do carro
## em cada tile fica em user://jogo.json (salva a cada 10 s, no menu e ao sair).
extends Node3D

const DEFAULT_TILE := "fatia"
const TILE_INICIAL := "anel1"
const BENCH_SECONDS := 20.0
const SAVE_JOGO := "user://jogo.json"
const AUTOSAVE_S := 10.0
const MENU := preload("res://menu/menu.gd")
const MINIMAPA := preload("res://minimapa/minimapa.gd")

static var tile_escolhido := ""  # sobrevive ao reload_current_scene da troca de mapa

@onready var car: Car = $Car
@onready var camera: Camera3D = $Camera
@onready var hud: Label = $HUD/Info
@onready var descobertas: Descobertas = $Descobertas

var spawn := Transform3D.IDENTITY
var tile := DEFAULT_TILE
var meta := {}
var _t := 0.0
var _frames: Array[float] = []
var _mode := ""
var _log: Array[String] = []
var _jogando := false
var _autosave_t := 0.0


func _ready() -> void:
	_setup_input()
	var args := OS.get_cmdline_user_args()
	if "--autotest-descoberta" in args:
		_mode = "descoberta"
	elif "--autotest" in args:
		_mode = "autotest"
	elif "--bench" in args:
		_mode = "bench"
	if _mode == "":
		tile = tile_escolhido if tile_escolhido != "" else _ler_save().get("ultimo_tile", TILE_INICIAL)
		if not ResourceLoader.exists("res://world/tiles/%s.glb" % tile):
			tile = DEFAULT_TILE
	var save := Descobertas.SAVE_PADRAO
	for arg in args:
		if arg.begins_with("--tile="):
			tile = arg.trim_prefix("--tile=")
		elif arg.begins_with("--save="):
			save = arg.trim_prefix("--save=")
	if _mode == "descoberta":
		DirAccess.remove_absolute(ProjectSettings.globalize_path(save))  # começa do zero
	var world: Node3D = load("res://world/tiles/%s.glb" % tile).instantiate()
	world.name = "Tile"
	add_child(world)
	meta = JSON.parse_string(FileAccess.get_file_as_string("res://world/tiles/%s.json" % tile))
	var s: Dictionary = meta["spawn"]
	spawn = Transform3D(Basis(Vector3.UP, -float(s["heading_from_north"])), Vector3(s["x"], s["y"], s["z"]))
	_add_bounds(float(meta["size_m"]) / 2.0)
	_apply_palette(world)
	descobertas.setup(tile, car, save)
	reset_car()
	if _mode == "bench":
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	elif _mode == "":
		var radar := MINIMAPA.new()
		add_child(radar)
		radar.setup(car, descobertas, $Environment.environment)
		var menu := MENU.new()
		add_child(menu)
		menu.setup(self)
		menu.abrir_inicio()


func reset_car(destino = null) -> void:
	var t: Transform3D = spawn if destino == null else destino
	car.global_transform = t
	car.linear_velocity = Vector3.ZERO
	car.angular_velocity = Vector3.ZERO
	camera.global_position = t.origin + t.basis.z * 6.5 + Vector3.UP * 2.4


# --- Save da posição (menu) ---

func tem_save() -> bool:
	return _ler_save().get("posicoes", {}).has(tile)


func continuar() -> void:
	var p: Dictionary = _ler_save()["posicoes"][tile]
	reset_car(Transform3D(Basis(Vector3.UP, float(p["rot_y"])), Vector3(p["x"], float(p["y"]) + 0.5, p["z"])))
	_jogando = true


func comecar() -> void:
	reset_car()
	_jogando = true
	salvar()


func salvar() -> void:
	if not _jogando:
		return
	_autosave_t = 0.0
	var d := _ler_save()
	var posicoes: Dictionary = d.get("posicoes", {})
	var o := car.global_position
	posicoes[tile] = {"x": o.x, "y": o.y, "z": o.z, "rot_y": car.global_rotation.y}
	d["versao"] = 1
	d["ultimo_tile"] = tile
	d["posicoes"] = posicoes
	FileAccess.open(SAVE_JOGO, FileAccess.WRITE).store_string(JSON.stringify(d, " "))


func trocar_mapa(novo: String) -> void:
	salvar()
	tile_escolhido = novo
	get_tree().paused = false
	get_tree().reload_current_scene()


func apagar_progresso() -> void:
	descobertas.apagar()
	if FileAccess.file_exists(SAVE_JOGO):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(SAVE_JOGO))
	_jogando = false
	reset_car()


func _ler_save() -> Dictionary:
	if not FileAccess.file_exists(SAVE_JOGO):
		return {}
	var d = JSON.parse_string(FileAccess.get_file_as_string(SAVE_JOGO))
	return d if d is Dictionary else {}


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		salvar()


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
	if _jogando:
		_autosave_t += delta
		if _autosave_t >= AUTOSAVE_S:
			salvar()
	match _mode:
		"autotest":
			_autotest()
		"bench":
			_bench(delta)
		"descoberta":
			_autotest_descoberta()
	hud.text = "%d km/h   %d FPS   %s   %s\n[W/S] acelerar/frear  [A/D] direção  [Espaço] freio de mão  [C] câmera  [R] reiniciar  [M] zoom do mapa  [Esc] menu" % [
		absi(roundi(car.speed() * 3.6)), Engine.get_frames_per_second(),
		RenderingServer.get_current_rendering_driver_name(), descobertas.contador()]


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


func _autotest_descoberta() -> void:
	# Põe o carro parado em cima de cada gatilho, um a cada 0,5 s, e no fim confere
	# se todos viraram descoberta e se o save tem os mesmos ids.
	var i := int(_t / 0.5)
	if i < descobertas.pontos.size():
		var p: Dictionary = descobertas.pontos[i]
		car.global_position = Vector3(p["x"], car.global_position.y, p["z"])
		car.linear_velocity = Vector3.ZERO
		return
	if _t < (descobertas.pontos.size() + 2) * 0.5:
		return
	var salvo: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(descobertas.save_path))
	var faltam: Array = descobertas.pontos.filter(func(p): return not descobertas.ids.has(p["id"]))
	print("DESCOBERTA pontos=%d descobertos=%d salvos=%d peso=%d limiar=%d faltam=%s" % [
		descobertas.pontos.size(), descobertas.ids.size(), salvo["descobertos"].size(),
		descobertas.peso(), descobertas.limiar(), faltam.map(func(p): return p["nome"])])
	print("CONTADOR ", descobertas.contador())
	get_tree().quit()


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
		"pausa": [KEY_ESCAPE, KEY_P], "mapa_zoom": [KEY_M],
	}
	var axes := {
		"acelerar": [JOY_AXIS_TRIGGER_RIGHT, 1.0], "frear": [JOY_AXIS_TRIGGER_LEFT, 1.0],
		"esquerda": [JOY_AXIS_LEFT_X, -1.0], "direita": [JOY_AXIS_LEFT_X, 1.0],
	}
	var buttons := {"freio_de_mao": JOY_BUTTON_B, "camera": JOY_BUTTON_Y, "reiniciar": JOY_BUTTON_BACK,
		"pausa": JOY_BUTTON_START, "mapa_zoom": JOY_BUTTON_X}
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
