## Câmera de 3ª pessoa atrás do carro, com opção de capô (decisão 006).
extends Camera3D

@export var target: Car
@export var distance := 6.5
@export var height := 2.4
@export var smoothing := 6.0

var hood := false


func _physics_process(delta: float) -> void:
	if target == null:
		return
	var t := target.global_transform
	if hood:
		global_transform = t.translated_local(Vector3(0, 0.95, -0.4))
		return
	var back := t.basis.z
	back.y = 0.0
	back = back.normalized()
	var desired := t.origin + back * distance + Vector3.UP * height
	global_position = global_position.lerp(desired, clamp(smoothing * delta, 0.0, 1.0))
	look_at(t.origin + Vector3.UP * 1.0, Vector3.UP)
