// Objeto holografico translucido roxo que o ZodIA projeta.
// build: quanto da peca ja foi "desenhado" pelo laser (de baixo para cima).
// crack: falha/rachadura quando o Kumo interfere.
shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_opaque, blend_mix;

uniform vec4 tint : source_color = vec4(0.62, 0.30, 1.0, 1.0);
uniform vec4 edge_color : source_color = vec4(0.45, 0.95, 1.0, 1.0);
uniform float build : hint_range(0.0, 1.0) = 1.0;
uniform float y_min = -0.5;
uniform float y_max = 0.5;
uniform float alpha = 0.55;
uniform float crack : hint_range(0.0, 1.0) = 0.0;
uniform float flash : hint_range(0.0, 2.0) = 0.0;
uniform float fade : hint_range(0.0, 1.0) = 1.0;

varying vec3 local_pos;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void vertex() {
	local_pos = VERTEX;
}

void fragment() {
	float h = mix(y_min, y_max, build);
	if (local_pos.y > h + 0.001) {
		discard;
	}
	float facing = abs(dot(NORMAL, VIEW));
	float fres = pow(1.0 - clamp(facing, 0.0, 1.0), 2.0);
	float scan = 0.5 + 0.5 * sin(local_pos.y * 38.0 - TIME * 6.0);
	float edge = smoothstep(0.07, 0.0, h - local_pos.y) * (1.0 - step(0.999, build));

	vec3 col = tint.rgb * (0.62 + 0.25 * scan) + tint.rgb * fres * 0.9;
	float a = alpha + fres * 0.45 + scan * 0.06;

	if (crack > 0.0) {
		vec2 cell = floor(local_pos.xz * 5.0 + local_pos.y * 3.0);
		float n = hash(cell + floor(TIME * 9.0));
		float lines = step(0.9, fract((local_pos.x + local_pos.y * 0.7 - local_pos.z * 0.4) * 6.0 + n * 0.6));
		col = mix(col, vec3(1.3, 0.45, 1.1), lines * crack);
		a *= mix(1.0, 0.35 + 0.65 * n, crack);
	}

	col = mix(col, edge_color.rgb * 1.6, edge);
	col += vec3(flash);
	ALBEDO = col;
	ALPHA = clamp(a + edge, 0.0, 1.0) * fade;
}
