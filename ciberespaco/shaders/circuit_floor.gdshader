// Chao do ciberespaco: placa de circuito azul em volta do campinho.
// Trilhas retas e em 45 graus, vias (circulos) e chips escuros com contorno,
// pulsos de luz correndo para fora; ao longe as trilhas se desfazem em
// quadradinhos e somem no roxo do horizonte.
shader_type spatial;
render_mode unshaded;

uniform vec3 base_near : source_color = vec3(0.035, 0.035, 0.12);
uniform vec3 base_far : source_color = vec3(0.09, 0.04, 0.2);
uniform vec3 horizon : source_color = vec3(0.16, 0.07, 0.3);
uniform vec3 trace_a : source_color = vec3(0.2, 0.55, 1.0);
uniform vec3 trace_b : source_color = vec3(0.55, 0.35, 1.0);
uniform vec3 chip_body : source_color = vec3(0.06, 0.07, 0.2);
uniform float cell = 0.85;
uniform float island_r = 6.6;
uniform float band_end = 22.0;
uniform float fade_end = 34.0;

varying vec3 wp;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float seg(vec2 p, vec2 a, vec2 b) {
	vec2 pa = p - a; vec2 ba = b - a;
	float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
	return length(pa - ba * h);
}

void vertex() { wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

void fragment() {
	vec2 p = wp.xz;
	float d = length(p);
	vec2 g = p / cell;
	vec2 id = floor(g);
	vec2 f = fract(g);
	float h = hash(id);

	// tipo de peca da trilha
	float dist = 9.0;
	if (h < 0.2) dist = seg(f, vec2(0.0, 0.5), vec2(1.0, 0.5));
	else if (h < 0.4) dist = seg(f, vec2(0.5, 0.0), vec2(0.5, 1.0));
	else if (h < 0.58) dist = min(seg(f, vec2(0.0, 0.5), vec2(0.5, 0.0)), seg(f, vec2(0.5, 1.0), vec2(1.0, 0.5)));
	else if (h < 0.76) dist = min(seg(f, vec2(0.0, 0.5), vec2(0.5, 1.0)), seg(f, vec2(0.5, 0.0), vec2(1.0, 0.5)));
	else if (h < 0.86) dist = min(seg(f, vec2(0.0, 0.5), vec2(0.5, 0.5)), seg(f, vec2(0.5, 0.5), vec2(0.5, 0.0)));
	float lw = 0.05;
	float line = 1.0 - smoothstep(lw * 0.5, lw, dist);
	float halo = (1.0 - smoothstep(0.0, 0.3, dist)) * 0.3;
	float via = step(0.9, hash(id + 3.1)) * (1.0 - smoothstep(0.02, 0.05, abs(length(f - 0.5) - 0.11)));

	// densidade: cheia perto do campo, rareando ao longe
	float density = mix(0.85, 0.35, smoothstep(9.0, band_end, d));
	float active = step(hash(id + 5.7), density);

	// chips (blocos escuros com contorno e pinos)
	vec2 cg = p / (cell * 4.0);
	vec2 cid = floor(cg);
	vec2 cf = fract(cg);
	float ch = hash(cid + 9.0);
	vec2 hs = vec2(0.22 + 0.15 * hash(cid + 1.3), 0.18 + 0.15 * hash(cid + 2.7));
	vec2 q = abs(cf - 0.5);
	float in_chip = step(0.8, ch) * step(q.x, hs.x) * step(q.y, hs.y) * step(island_r + 1.5, d);
	float border = in_chip * (1.0 - step(0.025, min(hs.x - q.x, hs.y - q.y)));
	float pins = step(0.8, ch) * step(island_r + 1.5, d) * step(q.y, hs.y - 0.03) * step(hs.x, q.x) * step(q.x, hs.x + 0.06) * step(0.5, fract(cf.y * 14.0));

	float inner = smoothstep(island_r, island_r + 0.5, d);
	float diss = smoothstep(band_end, fade_end, d);
	float px = step(diss, hash(floor(p * 2.5)));
	float pulse = pow(0.5 + 0.5 * sin(d * 0.8 - TIME * 2.2 + h * 3.0), 8.0);
	vec3 tc = mix(trace_a, trace_b, step(0.78, hash(id * 0.37 + 1.0)));

	float I = (line * (0.5 + 1.3 * pulse) + halo + via * 0.9) * active * inner * px * (1.0 - in_chip);
	vec3 col = mix(base_near, base_far, smoothstep(8.0, 30.0, d));
	col = mix(col, chip_body, in_chip);
	col += tc * I;
	col += trace_a * (border * 1.1 + pins * 0.7) * px;
	col = mix(col, horizon, smoothstep(fade_end * 0.75, fade_end * 1.3, d));
	ALBEDO = col;
}
