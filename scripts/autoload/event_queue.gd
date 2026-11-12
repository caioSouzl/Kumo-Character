extends Node
## Fila de eventos da live.
## - Respeita a ordem de chegada dos presentes.
## - Despacha no maximo um evento a cada event_min_interval_sec (padrao 3 s).
## - Eventos "blocking" seguram a fila ate o jogo chamar finish(ev), para nao
##   cortar uma animacao longa; max_block_sec e a trava de seguranca.
## - Presentes "groupable" iguais e seguidos no fim da fila viram um so evento,
##   somando a quantidade (ex.: varias rosas = uma animacao de gorjeta).

signal event_started(ev: Dictionary)
signal event_finished(ev: Dictionary)
signal queue_changed

var paused := false

var _queue: Array[Dictionary] = []
var _current: Dictionary = {}
var _since_dispatch := 999.0
var _block_left := 0.0
var _next_id := 1


func enqueue_gift(gift_name: String, sender: String = "anonimo", count: int = 1) -> bool:
	var gift_id := GameConfig.resolve_gift_id(gift_name)
	if gift_id == "":
		push_warning("Presente sem evento configurado: %s" % gift_name)
		return false
	var def: Dictionary = GameConfig.gifts[gift_id]
	count = maxi(count, 1)
	if bool(def.get("groupable", false)) and not _queue.is_empty():
		var tail: Dictionary = _queue[-1]
		if tail["gift_id"] == gift_id:
			tail["count"] = int(tail["count"]) + count
			var senders: Array = tail["senders"]
			if not senders.has(sender):
				senders.append(sender)
			queue_changed.emit()
			return true
	var ev := {
		"id": _next_id,
		"gift_id": gift_id,
		"event": String(def.get("event", "")),
		"def": def,
		"count": count,
		"senders": [sender],
	}
	_next_id += 1
	_queue.append(ev)
	queue_changed.emit()
	return true


func _process(delta: float) -> void:
	_since_dispatch += delta
	if not _current.is_empty():
		_block_left -= delta
		if _block_left <= 0.0:
			push_warning("Evento %s passou do tempo maximo; liberando a fila." % _current["event"])
			finish(_current)
		return
	if paused or _queue.is_empty():
		return
	if _since_dispatch < GameConfig.num("event_min_interval_sec", 3.0):
		return
	var ev: Dictionary = _queue.pop_front()
	_since_dispatch = 0.0
	var def: Dictionary = ev["def"]
	if bool(def.get("blocking", false)):
		_current = ev
		_block_left = float(def.get("max_block_sec", 20.0))
	queue_changed.emit()
	event_started.emit(ev)


## O jogo chama quando a animacao de um evento "blocking" termina.
func finish(ev: Dictionary) -> void:
	if _current.is_empty() or _current["id"] != ev["id"]:
		return
	_current = {}
	event_finished.emit(ev)
	queue_changed.emit()


func current() -> Dictionary:
	return _current


func pending() -> Array[Dictionary]:
	return _queue.duplicate()


func clear() -> void:
	_queue.clear()
	queue_changed.emit()
