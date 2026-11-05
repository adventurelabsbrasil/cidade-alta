## Lugares feitos à mão (posto, farmácia…): override versionado em
## pipeline/lugares/<tile>.toml, transformado por pipeline/lugares_tile.py em
## world/tiles/<tile>.lugares.json. Ao carregar o tile:
##   1. tira da malha de prédios os triângulos dentro de cada pegada a demolir
##      (e refaz a colisão), sem tocar no .glb;
##   2. monta pisos, caixas e placas, assentados no terreno do próprio tile.
class_name Lugares
extends Node3D

const LIFT_CAIXA := 0.6  # caixa no chão afunda isso, pra não flutuar na ladeira

var _terreno := {}       # Vector2i(célula) -> altura, lida da malha do terreno
var _passo := 0.0
var _meio := 0.0
var _materiais := {}


func setup(tile_root: Node3D, tile: String, meta: Dictionary) -> void:
	var arq := "res://world/tiles/%s.lugares.json" % tile
	if not FileAccess.file_exists(arq):
		return
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(arq))
	var terreno := tile_root.get_node_or_null("terreno") as MeshInstance3D
	var predios := tile_root.get_node_or_null("predios") as MeshInstance3D
	if terreno == null:
		push_warning("lugares: tile sem terreno, nada montado")
		return
	_ler_terreno(terreno, float(meta["size_m"]))
	if predios != null:
		_demolir(predios, data["demolir"])
	for p in data["pecas"]:
		match p["tipo"]:
			"piso":
				_piso(p)
			"caixa":
				_caixa(p)
			"placa":
				_placa(p)


func altura(x: float, z: float) -> float:
	# Mesma grade e mesma diagonal dos triângulos do build_tile.py: (i,j)-(i+1,j+1).
	var e := (x + _meio) / _passo
	var n := (-z + _meio) / _passo
	var j := clampi(floori(e), 0, int(2 * _meio / _passo) - 1)
	var i := clampi(floori(n), 0, int(2 * _meio / _passo) - 1)
	var u := e - j
	var v := n - i
	var h00: float = _terreno.get(Vector2i(i, j), 0.0)
	var h01: float = _terreno.get(Vector2i(i, j + 1), h00)
	var h10: float = _terreno.get(Vector2i(i + 1, j), h00)
	var h11: float = _terreno.get(Vector2i(i + 1, j + 1), h00)
	if u >= v:
		return h00 + u * (h01 - h00) + v * (h11 - h01)
	return h00 + v * (h10 - h00) + u * (h11 - h10)


func _ler_terreno(terreno: MeshInstance3D, lado: float) -> void:
	var vs: PackedVector3Array = terreno.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	var n := int(round(sqrt(vs.size())))
	_meio = lado / 2.0
	_passo = lado / (n - 1)
	for p in vs:
		_terreno[Vector2i(roundi((-p.z + _meio) / _passo), roundi((p.x + _meio) / _passo))] = p.y


func _demolir(predios: MeshInstance3D, pegadas: Array) -> void:
	# Cada prédio do pipeline é um volume extrudado da pegada: todo triângulo dele
	# tem o centro dentro da pegada. Filtra só o índice; os vértices ficam.
	var polis: Array[PackedVector2Array] = []
	var caixas: Array[Rect2] = []
	for peg in pegadas:
		var pol := PackedVector2Array()
		for c in peg:
			pol.append(Vector2(c[0], c[1]))
		polis.append(pol)
		var r := Rect2(pol[0], Vector2.ZERO)
		for q in pol:
			r = r.expand(q)
		caixas.append(r)
	var antigo: Mesh = predios.mesh
	var novo := ArrayMesh.new()
	var tirados := 0
	for s in antigo.get_surface_count():
		var arrays := antigo.surface_get_arrays(s)
		var vs: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var idx: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		var fica := PackedInt32Array()
		fica.resize(idx.size())
		var k := 0
		for t in range(0, idx.size(), 3):
			var c := (vs[idx[t]] + vs[idx[t + 1]] + vs[idx[t + 2]]) / 3.0
			var c2 := Vector2(c.x, c.z)
			var sai := false
			for i in polis.size():
				if caixas[i].has_point(c2) and Geometry2D.is_point_in_polygon(c2, polis[i]):
					sai = true
					break
			if sai:
				tirados += 1
				continue
			fica[k] = idx[t]
			fica[k + 1] = idx[t + 1]
			fica[k + 2] = idx[t + 2]
			k += 3
		fica.resize(k)
		arrays[Mesh.ARRAY_INDEX] = fica
		novo.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		novo.surface_set_material(s, antigo.surface_get_material(s))
	predios.mesh = novo
	for corpo in predios.find_children("*", "CollisionShape3D", true, false):
		(corpo as CollisionShape3D).shape = novo.create_trimesh_shape()
	print("lugares: %d triângulos de prédio demolidos (%d pegadas)" % [tirados, pegadas.size()])


func _material(cor: String) -> StandardMaterial3D:
	if not _materiais.has(cor):
		var m := StandardMaterial3D.new()
		m.albedo_color = Color.html(cor)
		m.roughness = 0.95
		_materiais[cor] = m
	return _materiais[cor]


func _piso(p: Dictionary) -> void:
	var tris: Array = p["tris"]
	var lift := float(p["lift"])
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for t in range(0, tris.size(), 6):
		var a := Vector3(tris[t], 0, tris[t + 1])
		var b := Vector3(tris[t + 2], 0, tris[t + 3])
		var c := Vector3(tris[t + 4], 0, tris[t + 5])
		var tri := [a, b, c]
		for q in 3:
			tri[q].y = altura(tri[q].x, tri[q].z) + lift
		# Face pra cima: no Godot a frente é o sentido horário visto de fora.
		if (tri[1] - tri[0]).cross(tri[2] - tri[0]).y > 0:
			tri = [tri[0], tri[2], tri[1]]
		for q in 3:
			st.add_vertex(tri[q])
	st.generate_normals()
	var malha := st.commit()
	var mi := MeshInstance3D.new()
	mi.mesh = malha
	mi.material_override = _material(p["cor"])
	add_child(mi)
	var corpo := StaticBody3D.new()
	var forma := CollisionShape3D.new()
	forma.shape = malha.create_trimesh_shape()
	corpo.add_child(forma)
	add_child(corpo)


func _caixa(p: Dictionary) -> void:
	var tam: Array = p["tam"]
	var elev := float(p["elev"])
	var afunda := LIFT_CAIXA if elev == 0.0 else 0.0
	var h := float(tam[1]) + afunda
	var malha := BoxMesh.new()
	malha.size = Vector3(tam[0], h, tam[2])
	var x := float(p["x"])
	var z := float(p["z"])
	var base := altura(x, z) + elev - afunda
	var corpo := StaticBody3D.new()
	corpo.position = Vector3(x, base + h / 2.0, z)
	corpo.rotation.y = float(p["rot_y"])
	var mi := MeshInstance3D.new()
	mi.mesh = malha
	mi.material_override = _material(p["cor"])
	corpo.add_child(mi)
	# Peça alta (pilar, loja, totem) bate; faixa pintada e forro não.
	if elev < 2.0 and float(tam[1]) > 0.1:
		var forma := CollisionShape3D.new()
		var caixa := BoxShape3D.new()
		caixa.size = malha.size
		forma.shape = caixa
		corpo.add_child(forma)
	add_child(corpo)


func _placa(p: Dictionary) -> void:
	var x := float(p["x"])
	var z := float(p["z"])
	var l := Label3D.new()
	l.text = p["texto"]
	l.font_size = int(p["px"])
	l.pixel_size = 0.005
	l.outline_size = 0
	l.modulate = Color.html(p["cor"])
	l.double_sided = false
	l.position = Vector3(x, altura(x, z) + float(p["elev"]), z)
	l.rotation.y = float(p["rot_y"])
	add_child(l)
