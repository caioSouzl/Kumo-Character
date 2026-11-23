// Grama do campinho: verde vivo com manchas claras (luz) e escuras (sombra),
// pontinhos amarelados. Na borda a grama se desfaz em pixels com brilho azul
// e o circuito aparece por baixo: o campo se mistura com o espaco digital.
shader_type spatial;
render_mode diffuse_lambert, specular_disabled, cull_disabled;

uniform vec3 dark : source_color = vec3(0.2, 0.45, 0.15);
uniform vec3 mid : source_color = vec3(0.36, 0.66, 0.2);
uniform vec3 light : source_color = vec3(0.6, 0.82, 0.26);
uniform vec3 sun : source_color = vec3(0.78, 0.85, 0.35);
uniform float radius = 11.0;
uniform float fade = 1.8;
uniform vec3 digital : source_color = vec3(0.3, 0.75, 1.0);

varying vec3 wp;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p) {
	float v = 0.0; float a = 0.5;
	for (int i = 0; i < 4; i++) { v += noise(p) * a; p *= 2.03; a *= 0.5; }
	return v;
}

void vertex() { wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }

void fragment() {
	vec2 p = wp.xz;
	float n = fbm(p * 0.45);
	float d = fbm(p * 2.2 + 13.0);
	vec3 c = mix(dark, mid, smoothstep(0.25, 0.55, n));
	c = mix(c, light, smoothstep(0.55, 0.8, n) * 0.8);
	c *= 0.85 + 0.3 * d;
	float speck = step(0.93, hash(floor(p * 9.0)));
	c = mix(c, sun, speck * 0.5 * smoothstep(0.4, 0.7, n));
	float r = length(p);
	float ang = atan(p.y, p.x);
	float er = radius + sin(ang * 3.0 + 0.7) * 0.4 + sin(ang * 7.0 + 2.1) * 0.25 + sin(ang * 13.0) * 0.12;
	// transicao: pixels de 30 cm somem aos poucos, com contorno azul
	float t = smoothstep(er - fade, er + fade * 0.6, r + (noise(p * 0.7) - 0.5) * 1.4);
	float hz = hash(floor(p * 3.3));
	if (hz < t) {
		discard;
	}
	float edge = (1.0 - smoothstep(0.0, 0.16, hz - t)) * step(0.02, t);
	c = mix(c, c * vec3(0.6, 0.85, 1.1), t);
	c = mix(c, digital, edge * 0.7);
	ALBEDO = c;
	EMISSION = c * 0.22 + digital * edge * 0.9;
	ROUGHNESS = 1.0;
}
