## Carro arcade com peso (decisão 006): corpo rígido no Jolt + uma raycast por roda.
## Suspensão mola-amortecedor, aderência lateral limitada pela carga da roda e
## freio de mão que solta a traseira pro drift. Os três arquétipos usam este
## mesmo código; só os parâmetros mudam.
class_name Car
extends RigidBody3D

@export_group("Motor")
@export var engine_force := 7000.0      # N na arrancada
@export var top_speed := 44.0           # m/s (~160 km/h)
@export var reverse_speed := 8.0        # m/s
@export var brake_force := 11000.0      # N
@export var drag := 0.42                # arrasto aerodinâmico (N por (m/s)²)
@export var rolling := 150.0            # resistência à rolagem (N)

@export_group("Direção")
@export var max_steer := 0.55           # rad, parado
@export var high_speed_steer := 0.12    # rad, na velocidade máxima
@export var steer_speed := 3.5          # rad/s

@export_group("Suspensão")
@export var rest_length := 0.35
@export var wheel_radius := 0.31
@export var spring := 32000.0           # N/m
@export var damper := 2600.0            # N·s/m

@export_group("Aderência")
@export var front_grip := 0.85          # fração da velocidade lateral anulada por tick
@export var rear_grip := 0.80
@export var handbrake_rear_grip := 0.12
@export var friction := 1.3             # coeficiente: teto da força lateral = μ·carga

var steer := 0.0
var autopilot := {}                     # entradas forçadas (testes e benchmark)

@onready var wheels: Array[RayCast3D] = [$WheelFL, $WheelFR, $WheelRL, $WheelRR]
@onready var wheel_meshes: Array[Node3D] = [$WheelFL/Mesh, $WheelFR/Mesh, $WheelRL/Mesh, $WheelRR/Mesh]
var _spin := 0.0


func _ready() -> void:
	center_of_mass_mode = RigidBody3D.CENTER_OF_MASS_MODE_CUSTOM
	center_of_mass = Vector3(0, -0.25, 0)
	for w in wheels:
		w.target_position = Vector3(0, -(rest_length + wheel_radius), 0)
		w.add_exception(self)


func speed() -> float:
	return linear_velocity.dot(-global_basis.z)


func _input_axis(action_pos: String, action_neg: String) -> float:
	if autopilot.has(action_pos) or autopilot.has(action_neg):
		return autopilot.get(action_pos, 0.0) - autopilot.get(action_neg, 0.0)
	return Input.get_action_strength(action_pos) - Input.get_action_strength(action_neg)


func _physics_process(delta: float) -> void:
	var throttle := _input_axis("acelerar", "frear")
	var steer_in := _input_axis("esquerda", "direita")
	var handbrake: bool = autopilot.get("freio_de_mao", Input.is_action_pressed("freio_de_mao"))

	var v := speed()
	var steer_limit := lerpf(max_steer, high_speed_steer, clampf(absf(v) / top_speed, 0.0, 1.0))
	steer = move_toward(steer, steer_in * steer_limit, steer_speed * delta)

	var forward := -global_basis.z
	var load_per_wheel := mass * 9.8 / 4.0
	for i in wheels.size():
		var w := wheels[i]
		var is_front := i < 2
		var mesh := wheel_meshes[i]
		mesh.rotation.y = steer if is_front else 0.0
		if not w.is_colliding():
			mesh.position.y = -rest_length
			continue

		var hit := w.get_collision_point()
		var normal := w.get_collision_normal()
		var dist := w.global_position.distance_to(hit) - wheel_radius
		mesh.position.y = -dist
		var offset := w.global_position - global_position
		var point_vel := linear_velocity + angular_velocity.cross(offset)

		# Suspensão
		var compression := rest_length - dist
		var susp := spring * compression - damper * point_vel.dot(normal)
		susp = maxf(susp, 0.0)
		apply_force(normal * susp, offset)

		# Base da roda: dianteiras giram com a direção.
		var wheel_fwd := forward.rotated(global_basis.y, steer) if is_front else forward
		wheel_fwd = (wheel_fwd - normal * wheel_fwd.dot(normal)).normalized()
		var wheel_right := wheel_fwd.cross(normal).normalized()

		# Aderência lateral: anula parte da velocidade de lado, com teto pela carga.
		var grip := front_grip if is_front else (handbrake_rear_grip if handbrake else rear_grip)
		var lat_vel := point_vel.dot(wheel_right)
		var lat_force := -lat_vel * grip * load_per_wheel / (9.8 * delta) * 0.25
		var cap := friction * maxf(susp, load_per_wheel * 0.3)
		apply_force(wheel_right * clampf(lat_force, -cap, cap), offset)

		# Tração dianteira (compacto popular) e freio nas quatro.
		var long_force := 0.0
		if throttle > 0.0:
			if v < -0.5:
				long_force = brake_force * throttle / 4.0
			elif is_front:
				long_force = engine_force * throttle * clampf(1.0 - v / top_speed, 0.0, 1.0) / 2.0
		elif throttle < 0.0:
			if v > 0.5:
				long_force = brake_force * throttle / 4.0
			elif is_front:
				long_force = engine_force * 0.5 * throttle * clampf(1.0 + v / reverse_speed, 0.0, 1.0) / 2.0
		if handbrake and not is_front:
			long_force -= signf(v) * brake_force * 0.35 / 2.0
		# Sem pedal e quase parado: segura o carro na ladeira (a cidade é em morro).
		if is_zero_approx(throttle) and absf(v) < 2.0:
			long_force = -point_vel.dot(wheel_fwd) * load_per_wheel / (9.8 * delta) * 0.5
		apply_force(wheel_fwd * long_force, offset)

	# Arrasto e rolagem
	var vel := linear_velocity
	apply_central_force(-vel * vel.length() * drag)
	if vel.length() > 0.2:
		apply_central_force(-vel.normalized() * rolling)

	_spin += v * delta / wheel_radius
	for m in wheel_meshes:
		m.get_child(0).rotation.x = -_spin
