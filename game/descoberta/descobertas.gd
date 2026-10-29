## Descoberta por proximidade (decisão 008): cada ponto tem uma zona invisível na rua
## mais próxima; o carro entra nela e aparece um cartão com o nome real do lugar.
## Landmark (decisão 010) vale 2 e tem cartão próprio. Abrir o anel 2 pede o limiar
## do anel (decisão 011); na v0 o jogo só avisa "anel 2 em breve".
## Os pontos vêm de world/tiles/<tile>.pontos.json (pipeline/pontos_tile.py).
class_name Descobertas
extends CanvasLayer

signal descoberto(ponto: Dictionary)

const RAIO_M := 40.0            # raio da zona, medido no plano (sem altura)
const CARTAO_S := 4.0           # tempo do cartão na tela
const SAVE_PADRAO := "user://descobertas.json"

var pontos: Array = []
var anel := {}                  # resumo do anel inteiro: pontos, peso_total, limiar
var ids := {}                   # id -> true, tudo o que já foi descoberto (todos os tiles)
var save_path := SAVE_PADRAO
var alvo: Node3D

var _fila: Array[Dictionary] = []
var _cartao_t := 0.0
var _anel_avisado := false
var _cartao: PanelContainer
var _titulo: Label
var _nome: Label
var _sub: Label


func setup(tile: String, carro: Node3D, caminho_save := SAVE_PADRAO) -> void:
	alvo = carro
	save_path = caminho_save
	var arq := "res://world/tiles/%s.pontos.json" % tile
	if FileAccess.file_exists(arq):
		var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(arq))
		pontos = data["pontos"]
		anel = data["anel"]
	_carregar()
	_anel_avisado = peso() >= limiar()
	_montar_cartao()


func peso() -> int:
	# O peso sai do id: landmark vale 2 (decisão 010). Assim o save guarda só ids.
	var total := 0
	for id in ids:
		total += 2 if String(id).begins_with("landmark:") else 1
	return total


func limiar() -> int:
	return int(anel.get("limiar", 0))


func contador() -> String:
	if anel.is_empty():
		return ""
	var txt := "Descobertas %d/%d   anel 2: %d/%d" % [ids.size(), int(anel["pontos"]), peso(), limiar()]
	return txt + ("  (em breve)" if peso() >= limiar() else "")


func _physics_process(_delta: float) -> void:
	if alvo == null:
		return
	var p := alvo.global_position
	for ponto in pontos:
		if ids.has(ponto["id"]):
			continue
		if Vector2(p.x - ponto["x"], p.z - ponto["z"]).length() <= RAIO_M:
			_descobrir(ponto)


func _descobrir(ponto: Dictionary) -> void:
	ids[ponto["id"]] = true
	_salvar()
	_fila.append(ponto)
	descoberto.emit(ponto)
	if not _anel_avisado and peso() >= limiar():
		_anel_avisado = true
		_fila.append({"aviso": "Anel 2 em breve"})


func _process(delta: float) -> void:
	if _cartao_t > 0.0:
		_cartao_t -= delta
		_cartao.modulate.a = clampf(_cartao_t / 0.4, 0.0, 1.0)
		if _cartao_t <= 0.0:
			_cartao.visible = false
	elif not _fila.is_empty():
		_mostrar(_fila.pop_front())


func _mostrar(ponto: Dictionary) -> void:
	if ponto.has("aviso"):
		_titulo.text = "PROGRESSO"
		_nome.text = ponto["aviso"]
		_sub.text = "%d de %d para abrir o próximo anel" % [peso(), limiar()]
	else:
		_titulo.text = "LANDMARK" if ponto["landmark"] else "DESCOBERTA"
		_nome.text = ponto["nome"]
		_sub.text = ponto["categoria"]
	_titulo.modulate = Color(1.0, 0.8, 0.3) if ponto.get("landmark", false) else Color(0.8, 0.9, 1.0)
	_cartao.visible = true
	_cartao.modulate.a = 1.0
	_cartao_t = CARTAO_S


func _carregar() -> void:
	if not FileAccess.file_exists(save_path):
		return
	var data = JSON.parse_string(FileAccess.get_file_as_string(save_path))
	if data is Dictionary:
		for id in data.get("descobertos", []):
			ids[id] = true


func _salvar() -> void:
	# Grava a cada descoberta (decisão 008): JSON de ids em user://.
	var f := FileAccess.open(save_path, FileAccess.WRITE)
	f.store_string(JSON.stringify({"versao": 1, "descobertos": ids.keys()}, " "))


func _montar_cartao() -> void:
	_cartao = PanelContainer.new()
	var estilo := StyleBoxFlat.new()
	estilo.bg_color = Color(0.05, 0.07, 0.1, 0.82)
	estilo.set_corner_radius_all(6)
	estilo.set_content_margin_all(18)
	_cartao.add_theme_stylebox_override("panel", estilo)
	_cartao.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	_cartao.position.y = 60
	_cartao.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_cartao.visible = false
	var caixa := VBoxContainer.new()
	caixa.alignment = BoxContainer.ALIGNMENT_CENTER
	_titulo = _rotulo(16)
	_nome = _rotulo(32)
	_sub = _rotulo(16)
	_sub.modulate = Color(1, 1, 1, 0.7)
	for l in [_titulo, _nome, _sub]:
		caixa.add_child(l)
	_cartao.add_child(caixa)
	add_child(_cartao)


func _rotulo(tamanho: int) -> Label:
	var l := Label.new()
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.add_theme_font_size_override("font_size", tamanho)
	return l
