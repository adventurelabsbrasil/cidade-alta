## Radar no canto: uma câmera ortográfica olha a cidade de cima, presa ao carro e
## girando com ele (a frente do carro é sempre pra cima). Por cima vão a seta do
## carro, o norte e as descobertas que faltam; as longe ficam presas na borda.
## [M] / X do gamepad troca o zoom.
extends CanvasLayer

const TAM := 260                         # px do radar na tela
const ZOOMS := [200.0, 400.0, 800.0]     # metros mostrados de borda a borda
const ALTURA := 500.0

var carro: Node3D
var descobertas: Node
var zoom := 1

var _cam: Camera3D
var _desenho: Control
var _proxima: Label


func setup(alvo: Node3D, desc: Node, ambiente: Environment) -> void:
	carro = alvo
	descobertas = desc
	layer = 5
	process_mode = Node.PROCESS_MODE_ALWAYS  # continua certo atrás do menu (jogo pausado)
	var raiz := Control.new()
	raiz.anchor_left = 1.0
	raiz.anchor_top = 1.0
	raiz.anchor_right = 1.0
	raiz.anchor_bottom = 1.0
	raiz.offset_left = -TAM - 20
	raiz.offset_top = -TAM - 52
	raiz.offset_right = -20
	raiz.offset_bottom = -52
	raiz.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(raiz)

	var vp := SubViewport.new()
	vp.size = Vector2i(TAM, TAM)
	vp.msaa_3d = Viewport.MSAA_2X
	add_child(vp)
	_cam = Camera3D.new()
	_cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	_cam.far = ALTURA + 300.0
	var amb := ambiente.duplicate() as Environment
	amb.fog_enabled = false                       # de cima a névoa só lava a cor
	_cam.environment = amb
	vp.add_child(_cam)

	var imagem := TextureRect.new()
	imagem.texture = vp.get_texture()
	imagem.set_anchors_preset(Control.PRESET_FULL_RECT)
	imagem.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mat := ShaderMaterial.new()
	mat.shader = Shader.new()
	mat.shader.code = """shader_type canvas_item;
void fragment() {
	if (length(UV - vec2(0.5)) > 0.5) discard;
	COLOR = texture(TEXTURE, UV);
}"""
	imagem.material = mat
	raiz.add_child(imagem)

	_desenho = Desenho.new()
	_desenho.radar = self
	_desenho.set_anchors_preset(Control.PRESET_FULL_RECT)
	_desenho.mouse_filter = Control.MOUSE_FILTER_IGNORE
	raiz.add_child(_desenho)

	_proxima = Label.new()
	_proxima.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_proxima.add_theme_font_size_override("font_size", 16)
	_proxima.add_theme_color_override("font_outline_color", Color.BLACK)
	_proxima.add_theme_constant_override("outline_size", 6)
	_proxima.position = Vector2(-240, TAM + 6)   # cresce pra esquerda, nunca sai da tela
	_proxima.size = Vector2(TAM + 240, 24)
	raiz.add_child(_proxima)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("mapa_zoom"):
		zoom = (zoom + 1) % ZOOMS.size()


func _process(_delta: float) -> void:
	if carro == null:
		return
	var yaw := carro.global_rotation.y
	# Basis(X, -90°) faz a câmera olhar pra baixo com o "pra cima" da tela = frente (-Z).
	_cam.global_transform = Transform3D(
		Basis(Vector3.UP, yaw) * Basis(Vector3.RIGHT, -PI / 2),
		carro.global_position + Vector3.UP * ALTURA)
	_cam.size = ZOOMS[zoom]
	_desenho.queue_redraw()
	_proxima.text = _texto_proxima()


## Posição na tela (relativa ao centro, em px) de um ponto do mundo.
func na_tela(x: float, z: float) -> Vector2:
	var b := Basis(Vector3.UP, carro.global_rotation.y)
	var rel := Vector3(x - carro.global_position.x, 0.0, z - carro.global_position.z)
	return Vector2(rel.dot(b.x), rel.dot(b.z)) * (TAM / ZOOMS[zoom])


func _texto_proxima() -> String:
	var melhor := {}
	var dist := INF
	var p := carro.global_position
	for ponto in descobertas.pontos:
		if descobertas.ids.has(ponto["id"]):
			continue
		var d := Vector2(p.x - ponto["x"], p.z - ponto["z"]).length()
		if d < dist:
			dist = d
			melhor = ponto
	if melhor.is_empty():
		return "Tudo descoberto aqui!" if not descobertas.pontos.is_empty() else ""
	var m := "%d m" % roundi(dist) if dist < 1000.0 else "%.1f km" % (dist / 1000.0)
	return "Próxima: %s — %s   [M] zoom" % [melhor["nome"], m]


class Desenho extends Control:
	var radar

	func _draw() -> void:
		var c := size / 2.0
		var r := size.x / 2.0
		draw_arc(c, r - 1.5, 0, TAU, 64, Color(0.05, 0.07, 0.1, 0.9), 3.0, true)
		# Descobertas que faltam: dentro do radar no lugar certo, fora presas na borda.
		for ponto in radar.descobertas.pontos:
			if radar.descobertas.ids.has(ponto["id"]):
				continue
			var v: Vector2 = radar.na_tela(ponto["x"], ponto["z"])
			var longe := v.length() > r - 8.0
			if longe:
				v = v.normalized() * (r - 8.0)
			var cor := Color(1.0, 0.75, 0.2) if ponto["landmark"] else Color(1.0, 0.95, 0.4)
			draw_circle(c + v, 4.0 if longe else 6.0, Color.BLACK)
			draw_circle(c + v, 2.5 if longe else 4.5, cor)
		# Norte: direção -Z do mundo, girada pro referencial do carro.
		var n: Vector2 = radar.na_tela(radar.carro.global_position.x, radar.carro.global_position.z - 1.0)
		var pn := c + n.normalized() * (r - 14.0)
		draw_circle(pn, 10.0, Color(0.05, 0.07, 0.1, 0.9))
		draw_string(ThemeDB.fallback_font, pn + Vector2(-5, 5), "N", HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color(1, 0.4, 0.4))
		# Carro: seta fixa apontando pra cima.
		var seta := PackedVector2Array([c + Vector2(0, -11), c + Vector2(8, 8), c + Vector2(0, 4), c + Vector2(-8, 8)])
		draw_colored_polygon(seta, Color.WHITE)
		draw_polyline(seta + PackedVector2Array([seta[0]]), Color.BLACK, 2.0, true)
