extends Node
## Carrega config/game.json, config/gifts.json e config/projects.json.
## Valores de jogo, presentes e projetos ficam nos JSONs, nunca fixos no codigo.

const GAME_PATH := "res://config/game.json"
const GIFTS_PATH := "res://config/gifts.json"
const PROJECTS_PATH := "res://config/projects.json"

var game: Dictionary = {}
var gifts: Dictionary = {}
var projects: Array = []
## nome enviado pela live (minusculo) -> id do presente
var _names: Dictionary = {}


func _ready() -> void:
	game = _load_json(GAME_PATH)
	gifts = _load_json(GIFTS_PATH).get("gifts", {})
	projects = _load_json(PROJECTS_PATH).get("projects", [])
	for gift_id in gifts:
		_names[String(gift_id).to_lower()] = gift_id
		var def: Dictionary = gifts[gift_id]
		_names[String(def.get("label", gift_id)).to_lower()] = gift_id
		for n in def.get("tiktok_names", []):
			_names[String(n).to_lower()] = gift_id


func _load_json(path: String) -> Dictionary:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("Nao foi possivel abrir %s" % path)
		return {}
	var data: Variant = JSON.parse_string(f.get_as_text())
	if typeof(data) != TYPE_DICTIONARY:
		push_error("JSON invalido em %s" % path)
		return {}
	return data


func num(key: String, default_value: float = 0.0) -> float:
	return float(game.get(key, default_value))


func value(key: String, default_value: Variant = null) -> Variant:
	return game.get(key, default_value)


## Le um valor dentro de um grupo: sub("battery", "per_like", 0.4)
func sub(group: String, key: String, default_value: Variant = null) -> Variant:
	var g: Variant = game.get(group, {})
	if typeof(g) != TYPE_DICTIONARY:
		return default_value
	return (g as Dictionary).get(key, default_value)


## Sorteia entre [min, max] de um par configurado.
func range_pick(group: String, key: String, fallback: Vector2, rng: RandomNumberGenerator) -> float:
	var r: Variant = sub(group, key, [fallback.x, fallback.y])
	if typeof(r) == TYPE_ARRAY and (r as Array).size() >= 2:
		return rng.randf_range(float(r[0]), float(r[1]))
	return rng.randf_range(fallback.x, fallback.y)


## Aceita o id, o label ou qualquer nome de tiktok_names. Retorna "" se nao houver evento.
func resolve_gift_id(gift_name: String) -> String:
	return String(_names.get(gift_name.strip_edges().to_lower(), ""))


func gift_ids() -> Array:
	var ids := gifts.keys()
	ids.sort()
	return ids
