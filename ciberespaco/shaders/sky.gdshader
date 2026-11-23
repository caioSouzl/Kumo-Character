// Ceu roxo escuro com nuvens suaves perto do horizonte.
shader_type sky;

uniform vec3 top_color : source_color = vec3(0.04, 0.02, 0.1);
uniform vec3 horizon_color : source_color = vec3(0.2, 0.09, 0.36);
uniform vec3 cloud_color : source_color = vec3(0.36, 0.2, 0.55);

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1, 0)), u.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), u.x), u.y);
}

void sky() {
	float y = EYEDIR.y;
	vec3 c = mix(horizon_color, top_color, smoothstep(-0.05, 0.45, y));
	vec2 uv = EYEDIR.xz / max(y + 0.25, 0.05);
	float n = noise(uv * 1.5 + TIME * 0.01) * 0.6 + noise(uv * 3.7) * 0.4;
	float band = smoothstep(0.35, 0.0, abs(y - 0.06));
	c = mix(c, cloud_color, smoothstep(0.5, 0.8, n) * band * 0.7);
	float star = step(0.997, hash(floor(EYEDIR.xz * 300.0 / max(y, 0.1)))) * smoothstep(0.15, 0.5, y);
	COLOR = c + vec3(star * 0.6);
}
