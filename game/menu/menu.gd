## Menu de início e de pausa: continuar do save, voltar ao início, trocar de mapa,
## salvar e sair. O jogo fica pausado enquanto o menu está aberto.
## Esc, P ou Start do gamepad abrem a pausa.
extends CanvasLayer

const MAPAS := {
	"anel1": "Cidade toda (3 km)",
	"fatia": "Quarteirão da Borges",
	"piloto-15nov": "Rua 15 de Novembro",
}

var jogo: Node                  # main.gd
var _modo := ""                 # "inicio" ou "pausa"
var _confirmar_apagar := false
var _titulo: Label
var _aviso: Label
var _botoes: VBoxContainer


func setup(main: Node) -> void:
	jogo = main
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 10
	_montar()


func abrir_inicio(aviso := "") -> void:
	_modo = "inicio"
	_abrir("CIDADE ALTA", aviso, [
		["Continuar de onde parou", _continuar, jogo.tem_save()],
		["Começar do início", _comecar, true],
		["Mapa: %s" % MAPAS.get(jogo.tile, jogo.tile), _trocar_mapa, true],
		["Tem certeza? Aperte de novo" if _confirmar_apagar else "Apagar descobertas", _apagar, true],
		["Sair", _sair, true],
	])


func abrir_pausa(aviso := "") -> void:
	_modo = "pausa"
	_abrir("PAUSA", aviso, [
		["Continuar", _fechar, true],
		["Voltar ao início da rua", _voltar_inicio, true],
		["Salvar", _salvar, true],
		["Menu inicial", _menu_inicial, true],
		["Sair (salva antes)", _sair, true],
	])


func _unhandled_input(event: InputEvent) -> void:
	if not event.is_action_pressed("pausa"):
		return
	if not visible:
		abrir_pausa()
	elif _modo == "pausa":
		_fechar()
	get_viewport().set_input_as_handled()


func _abrir(titulo: String, aviso: String, itens: Array) -> void:
	_titulo.text = titulo
	_aviso.text = aviso
	_aviso.visible = aviso != ""
	for b in _botoes.get_children():
		_botoes.remove_child(b)
		b.queue_free()
	var primeiro: Button = null
	for item in itens:
		var b := Button.new()
		b.text = item[0]
		b.disabled = not item[2]
		b.custom_minimum_size = Vector2(380, 52)
		b.add_theme_font_size_override("font_size", 22)
		b.pressed.connect(item[1])
		_botoes.add_child(b)
		if primeiro == null and not b.disabled:
			primeiro = b
	visible = true
	get_tree().paused = true
	if primeiro:
		primeiro.grab_focus.call_deferred()


func _fechar() -> void:
	visible = false
	get_tree().paused = false


func _continuar() -> void:
	jogo.continuar()
	_fechar()


func _comecar() -> void:
	jogo.comecar()
	_fechar()


func _trocar_mapa() -> void:
	var nomes := MAPAS.keys()
	jogo.trocar_mapa(nomes[(nomes.find(jogo.tile) + 1) % nomes.size()])


func _apagar() -> void:
	if not _confirmar_apagar:
		_confirmar_apagar = true
		abrir_inicio()
		return
	_confirmar_apagar = false
	jogo.apagar_progresso()
	abrir_inicio("Descobertas apagadas. Começando do zero!")


func _voltar_inicio() -> void:
	jogo.reset_car()
	_fechar()


func _salvar() -> void:
	jogo.salvar()
	abrir_pausa("Jogo salvo ✓")


func _menu_inicial() -> void:
	jogo.salvar()
	_confirmar_apagar = false
	abrir_inicio()


func _sair() -> void:
	jogo.salvar()
	get_tree().quit()


func _montar() -> void:
	var fundo := ColorRect.new()
	fundo.color = Color(0, 0, 0, 0.45)
	fundo.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(fundo)
	var centro := CenterContainer.new()
	centro.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(centro)
	var painel := PanelContainer.new()
	var estilo := StyleBoxFlat.new()
	estilo.bg_color = Color(0.05, 0.07, 0.1, 0.9)
	estilo.set_corner_radius_all(8)
	estilo.set_content_margin_all(28)
	painel.add_theme_stylebox_override("panel", estilo)
	centro.add_child(painel)
	var caixa := VBoxContainer.new()
	caixa.add_theme_constant_override("separation", 12)
	painel.add_child(caixa)
	_titulo = Label.new()
	_titulo.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_titulo.add_theme_font_size_override("font_size", 40)
	caixa.add_child(_titulo)
	_aviso = Label.new()
	_aviso.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_aviso.add_theme_font_size_override("font_size", 18)
	_aviso.modulate = Color(1.0, 0.85, 0.4)
	caixa.add_child(_aviso)
	_botoes = VBoxContainer.new()
	_botoes.add_theme_constant_override("separation", 10)
	caixa.add_child(_botoes)
	visible = false
