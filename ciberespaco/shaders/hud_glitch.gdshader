// Sobreposicao dos quadros do ZodIA: le a tela por baixo e aplica
// linhas de varredura de holograma, separacao RGB e cortes de glitch.
// glitch = forca do glitch (0 parado, 1 forte); scan = linhas de varredura.
shader_type canvas_item;

uniform sampler2D screen_tex : hint_screen_texture, filter_linear;
uniform float glitch : hint_range(0.0, 1.0) = 0.0;
uniform float scan : hint_range(0.0, 1.0) = 0.35;
uniform vec4 tint : source_color = vec4(1.0, 0.25, 0.85, 1.0);

float hash(float n) { return fract(sin(n) * 43758.5453); }

void fragment() {
	vec2 uv = SCREEN_UV;
	float t = floor(TIME * 24.0);
	// faixas horizontais que pulam para o lado
	float band = floor(UV.y * 14.0);
	float jump = step(1.0 - glitch * 0.55, hash(band * 7.1 + t)) * (hash(band + t * 3.3) - 0.5);
	uv.x += jump * 0.06 * glitch;
	// separacao RGB
	float split = (0.002 + 0.012 * glitch) * (0.6 + 0.4 * hash(t));
	vec3 c;
	c.r = texture(screen_tex, uv + vec2(split, 0.0)).r;
	c.g = texture(screen_tex, uv).g;
	c.b = texture(screen_tex, uv - vec2(split, 0.0)).b;
	// linhas de varredura que descem
	float line = 0.5 + 0.5 * sin((UV.y * 160.0 - TIME * 6.0) * 3.14159);
	c *= 1.0 - scan * 0.22 * line;
	// faixa clara correndo de cima para baixo
	float sweep = smoothstep(0.06, 0.0, abs(fract(TIME * 0.35) - UV.y));
	c += tint.rgb * sweep * 0.18 * scan;
	// blocos que somem no glitch forte
	float blk = step(0.93, hash(floor(UV.x * 18.0) + band * 13.0 + t)) * glitch;
	c = mix(c, tint.rgb * 0.9, blk * 0.6);
	COLOR = vec4(c, 1.0);
}
