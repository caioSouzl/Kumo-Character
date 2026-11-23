// Chao do ciberespaco: trilhas de circuito que correm para o horizonte e se
// desfazem aos poucos em pontos, ate sumir no ceu roxo escuro.
shader_type spatial;
render_mode unshaded;

uniform vec4 base_color : source_color = vec4(0.06, 0.02, 0.13, 1.0);
uniform vec4 line_a : source_color = vec4(0.15, 0.65, 1.0, 1.0);
uniform vec4 line_b : source_color = vec4(0.75, 0.30, 1.0, 1.0);
uniform vec4 horizon_color : source_color = vec4(0.07, 0.02, 0.16, 1.0);
uniform float cell = 1.1;
uniform float clear_radius = 5.4;
uniform float fade_start = 9.0;
uniform float fade_end = 30.0;

varying vec3 wpos;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 p = wpos.xz / cell;
	vec2 id = floor(p);
	vec2 f = fract(p);
	float d = length(wpos.xz);

	// trilhas: a maioria aponta para fora do centro (rumo ao horizonte)
	vec2 dir = abs(wpos.x) > abs(wpos.z) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
	float r = hash(id);
	float lw = 0.055;
	float along = dir.x > 0.5 ? step(abs(f.y - 0.5), lw) : step(abs(f.x - 0.5), lw);
	float across = dir.x > 0.5 ? step(abs(f.x - 0.5), lw) : step(abs(f.y - 0.5), lw);
	float trace = along * step(0.45, hash(vec2(dir.x > 0.5 ? id.y : id.x, 3.0)));
	trace = max(trace, across * step(0.86, r));
	float pad = step(length(f - 0.5), 0.1) * step(0.82, hash(id + 7.0));
	trace = max(trace, pad);

	float pulse = 0.5 + 0.5 * sin(d * 1.4 - TIME * 2.4 + r * 6.283);
	vec3 lc = mix(line_a.rgb, line_b.rgb, step(0.6, hash(id + 3.0)));

	// desfaz em pontos conforme se afasta
	float dissolve = smoothstep(fade_start, fade_end, d);
	float dots = step(dissolve * 1.05, hash(floor(p * 5.0)));
	float inner = smoothstep(clear_radius, clear_radius + 1.2, d);
	float glow = trace * dots * inner * (0.35 + 0.9 * pulse);

	vec3 grid = vec3(0.10, 0.05, 0.22) * (step(0.97, f.x) + step(0.97, f.y)) * inner;
	vec3 col = base_color.rgb + grid + lc * glow;
	col = mix(col, horizon_color.rgb, smoothstep(fade_start * 0.8, fade_end, d));
	ALBEDO = col;
}
