extends Node
## Conector da live (desligado por padrao em config/game.json -> live_connector).
## Conecta a um WebSocket local e espera mensagens JSON assim:
##   {"gift": "Rose", "user": "fulano", "count": 5}
## Qualquer ponte (tiktok-live-connector, TikFinity etc.) que traduza os presentes
## da live para esse formato funciona. O TikTok nao tem API publica oficial para
## presentes em tempo real, entao a ponte fica fora do jogo e pode ser trocada.

signal status_changed(text: String)

var _ws := WebSocketPeer.new()
var _enabled := false
var _url := ""
var _retry := 0.0
var _last_state := -1


func _ready() -> void:
	var c: Dictionary = GameConfig.value("live_connector", {})
	_enabled = bool(c.get("enabled", false))
	_url = String(c.get("url", "ws://127.0.0.1:21213"))
	if _enabled:
		_ws.connect_to_url(_url)


func is_enabled() -> bool:
	return _enabled


func _process(delta: float) -> void:
	if not _enabled:
		return
	_ws.poll()
	var state := _ws.get_ready_state()
	if state != _last_state:
		_last_state = state
		match state:
			WebSocketPeer.STATE_OPEN:
				status_changed.emit("Live conectada")
			WebSocketPeer.STATE_CLOSED:
				status_changed.emit("Live desconectada")
	match state:
		WebSocketPeer.STATE_OPEN:
			while _ws.get_available_packet_count() > 0:
				_handle(_ws.get_packet().get_string_from_utf8())
		WebSocketPeer.STATE_CLOSED:
			_retry -= delta
			if _retry <= 0.0:
				_retry = 3.0
				_ws = WebSocketPeer.new()
				_ws.connect_to_url(_url)


func _handle(text: String) -> void:
	var msg: Variant = JSON.parse_string(text)
	if typeof(msg) != TYPE_DICTIONARY:
		return
	var d: Dictionary = msg
	var gift := String(d.get("gift", d.get("giftName", "")))
	if gift == "":
		return
	var user := String(d.get("user", d.get("nickname", "anonimo")))
	var count := int(d.get("count", d.get("repeatCount", 1)))
	EventQueue.enqueue_gift(gift, user, count)
