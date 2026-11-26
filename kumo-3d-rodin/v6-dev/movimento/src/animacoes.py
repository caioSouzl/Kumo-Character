"""Caminhada, corrida e pulo do Kumo, com o IK dos pés, a cabeça estável e a cauda balançando.

  blender --background kumo_v8_movimento.blend --python animacoes.py -- <relatório.json>

Ações (24 quadros por segundo, no lugar, sem andar de verdade: o jogo move o personagem):
- Caminhar: 24 quadros (1 s), em loop. Passo de 0,20 m; velocidade no jogo 0,40 m/s.
- Correr: 16 quadros (0,67 s), em loop. Passo de 0,32 m, com fase no ar; velocidade 0,96 m/s.
- Pular: 36 quadros (1,5 s): preparo, impulso, no ar (40 cm), queda, pouso e volta.
As poses são escritas em coordenadas do mundo (o Kumo olha para -Y) e convertidas para o espaço de cada osso.
"""
import bpy, sys, json, math
from mathutils import Vector, Matrix, Quaternion

REL = sys.argv[sys.argv.index('--') + 1]
sc = bpy.context.scene; sc.render.fps = 24
rig = bpy.data.objects['Kumo_Rig']; pb = rig.pose.bones; B = rig.data.bones
CAUDA = sorted(n.name for n in pb if n.name.startswith('tail_'))
REP = {}

def R3(n): return B[n].matrix_local.to_3x3()
def loc_mundo(n, v): return R3(n).inverted() @ Vector(v)
def rot_mundo(n, giros):           # giros: [(eixo do mundo, graus), ...], aplicados em ordem
    M = Matrix.Identity(3)
    for e, g in giros: M = Matrix.Rotation(math.radians(g), 3, e) @ M
    return (R3(n).inverted() @ M @ R3(n)).to_quaternion()

OSSOS = ['root', 'hips', 'spine', 'chest', 'neck', 'upper_arm.L', 'upper_arm.R', 'forearm.L', 'forearm.R',
         'pe_ik.L', 'pe_ik.R', 'MCH_cabeca_mundo', 'controle_olhos'] + CAUDA

def zera():
    for n in OSSOS:
        p = pb[n]; p.rotation_mode = 'QUATERNION'; p.rotation_quaternion = (1, 0, 0, 0); p.location = (0, 0, 0)

def chave(f, pose):
    """pose: {osso: (tipo, valor)}; tipos: loc (mundo), rot (giros no mundo), qloc (giro no espaço do osso), ctrl (posição local).
    Chaves especiais: _estavel (cabeça estável 0..1), _pe_L/_pe_R (ponta do pé, graus), _hips_rot (giros do quadril)."""
    zera()
    for n, item in pose.items():
        if n.startswith('_'): continue
        tipo, v = item
        if tipo == 'loc': pb[n].location = loc_mundo(n, v)
        elif tipo == 'rot': pb[n].rotation_quaternion = rot_mundo(n, v)
        elif tipo == 'qloc': pb[n].rotation_quaternion = v
        elif tipo == 'ctrl': pb[n].location = v
    for s_ in 'LR': pb[f'pe_ik.{s_}'].rotation_quaternion = rot_mundo(f'pe_ik.{s_}', [(X, pose.get(f'_pe_{s_}', 0.0))])
    if pose.get('_hips_rot'): pb['hips'].rotation_quaternion = rot_mundo('hips', pose['_hips_rot'])
    rig['cabeca_estavel'] = pose.get('_estavel', 0.0)
    for n in OSSOS:
        pb[n].keyframe_insert('location', frame=f, group=n); pb[n].keyframe_insert('rotation_quaternion', frame=f, group=n)
    rig.keyframe_insert('["cabeca_estavel"]', frame=f)

def cauda(f, periodo, lado, cima, fase=0.0, desenrolar=0.0):
    out = {}
    for i, n in enumerate(CAUDA):
        a = 2 * math.pi * (f / periodo) - i * 0.35 + fase
        k = 0.4 + 0.6 * i / len(CAUDA)                                   # a ponta balança mais
        q = Quaternion((0, 0, 1), math.radians(lado * k * math.sin(a))) @ Quaternion((1, 0, 0), math.radians(cima * math.sin(a * 2) - desenrolar))
        out[n] = ('qloc', q)
    return out

def nova_acao(nome, ini, fim):
    a = bpy.data.actions.get(nome)
    if a: bpy.data.actions.remove(a)
    a = bpy.data.actions.new(nome); a.use_fake_user = True
    rig.animation_data_create(); rig.animation_data.action = a
    a.use_frame_range = True; a.frame_start = ini; a.frame_end = fim
    return a

X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))

def pe(f, T, S, H, fase, roll=20):
    """posição e giro do pé no ciclo: apoio (anda para trás no chão) e balanço (sobe e volta para a frente)"""
    u = ((f / T) + fase) % 1.0
    if u < 0.5:                                    # apoio: de -S (frente) até +S (trás), no chão
        t = u / 0.5; y = -S + 2 * S * t; z = 0.0
        ang = -roll * max(0.0, (t - 0.8) / 0.2)    # no fim do apoio o calcanhar sobe
    else:                                          # balanço
        t = (u - 0.5) / 0.5; y = S - 2 * S * (0.5 - 0.5 * math.cos(math.pi * t)); z = H * math.sin(math.pi * t)
        ang = -roll * (1 - t) * 0.6 + 10 * max(0.0, (t - 0.8) / 0.2)
    return y, z, ang

# ---------------------------------------------------------------- caminhar
def andar(nome, T, S, H, desce, sobe, balanco, giro, incl, braco, cotovelo, estavel, cauda_lado, cauda_cima, desenrolar, voo=False, base=0.0):
    nova_acao(nome, 0, T)
    for f in range(0, T + 1):          # uma chave por quadro: o pé no apoio anda reto, sem a curva da interpolação
        pose = {}
        for s, fase in (('L', 0.0), ('R', 0.5)):
            y, z, ang = pe(f, T, S, H, fase)
            pose[f'pe_ik.{s}'] = ('loc', (0, y, z)); pose[f'_pe_{s}'] = ang
        u = f / T
        # quadril: desce no contato, sobe na passagem (no voo da corrida, sobe mais no meio do passo)
        zq = -desce * (0.5 + 0.5 * math.cos(4 * math.pi * u)) + sobe * (0.5 - 0.5 * math.cos(4 * math.pi * u))
        if voo: zq = -desce * max(0.0, math.cos(4 * math.pi * (u - 0.03))) + sobe * max(0.0, -math.cos(4 * math.pi * (u - 0.03)))
        xq = balanco * math.sin(2 * math.pi * u + math.pi / 2) * -1
        pose['hips'] = ('loc', (xq, 0, zq + base))        # base: joelhos sempre um pouco dobrados (a perna do Kumo é curta)
        g = giro * math.cos(2 * math.pi * u)                         # perna esquerda à frente: lado esquerdo para a frente
        pose['_hips_rot'] = [(Z, -g)]
        pose['spine'] = ('rot', [(X, incl * 0.6), (Z, g * 0.4)])
        pose['chest'] = ('rot', [(X, incl * 0.4), (Z, g * 0.5)])
        b = braco * math.cos(2 * math.pi * u)                         # braço oposto à perna
        pose['upper_arm.L'] = ('rot', [(X, b)]); pose['upper_arm.R'] = ('rot', [(X, -b)])
        pose['forearm.L'] = ('rot', [(X, -cotovelo)]); pose['forearm.R'] = ('rot', [(X, -cotovelo)])
        pose['_estavel'] = estavel
        pose.update(cauda(f, T, cauda_lado, cauda_cima, desenrolar=desenrolar))
        chave(f, pose)
    REP[nome] = dict(quadros=T, segundos=round(T / 24, 2), passo_m=round(2 * S, 3), velocidade_m_s=round(2 * S * 2 / (T / 24), 3))

andar('Caminhar', 24, 0.09, 0.05, 0.015, 0.01, 0.015, 6, 3, 18, 10, 0.7, 5, 1.5, 0, base=-0.025)
andar('Correr', 16, 0.13, 0.09, 0.03, 0.025, 0.01, 8, 10, 35, 55, 0.85, 7, 2.5, 4, voo=True, base=-0.045)

# ---------------------------------------------------------------- pular
nova_acao('Pular', 0, 36)
def pulo(f, raiz=0.0, quadril=0.0, incl=0.0, braco=0.0, cotovelo=0.0, pes=0.0, pes_tras=0.0, ponta=0.0, desenrolar=0.0, apertar=0.0):
    pose = {'root': ('loc', (0, 0, raiz)), 'hips': ('loc', (0, 0, quadril)),
            'spine': ('rot', [(X, incl * 0.6)]), 'chest': ('rot', [(X, incl * 0.4)]),
            'upper_arm.L': ('rot', [(X, braco), (Y, -10 if braco < 0 else 0)]), 'upper_arm.R': ('rot', [(X, braco), (Y, 10 if braco < 0 else 0)]),
            'forearm.L': ('rot', [(X, -cotovelo)]), 'forearm.R': ('rot', [(X, -cotovelo)]),
            'pe_ik.L': ('loc', (0, pes_tras, pes)), 'pe_ik.R': ('loc', (0, pes_tras, pes)),
            'controle_olhos': ('ctrl', (apertar, apertar, 0)), '_estavel': 0.8, '_pe_L': ponta, '_pe_R': ponta}
    pose.update(cauda(f, 36, 3, 0, desenrolar=desenrolar))
    chave(f, pose)
CHAVES_PULO = [
    (0, {}),
    (6, dict(quadril=-0.10, incl=15, braco=35, cotovelo=20, apertar=0.25)),            # preparo: agacha, braços para trás
    (8, dict(quadril=-0.11, incl=17, braco=40, cotovelo=20, apertar=0.3)),
    (11, dict(raiz=0.06, quadril=0.03, incl=-4, braco=-70, cotovelo=10, ponta=-25)),    # impulso: estica, braços para cima
    (14, dict(raiz=0.24, quadril=0.0, incl=-2, braco=-80, cotovelo=15, pes=0.05, ponta=-20, desenrolar=4)),
    (18, dict(raiz=0.40, quadril=0.0, incl=4, braco=-60, cotovelo=30, pes=0.10, pes_tras=0.02, ponta=-10, desenrolar=6)),   # topo: joelhos encolhidos
    (22, dict(raiz=0.34, quadril=0.0, incl=4, braco=-40, cotovelo=30, pes=0.07, ponta=-5, desenrolar=5)),
    (26, dict(raiz=0.08, quadril=0.01, incl=0, braco=-20, cotovelo=20, pes=0.0, ponta=5, desenrolar=2)),
    (28, dict(raiz=0.0, quadril=-0.09, incl=14, braco=10, cotovelo=25, apertar=0.5)),     # pouso: amortece
    (31, dict(raiz=0.0, quadril=-0.06, incl=9, braco=5, cotovelo=15, apertar=0.2)),
    (36, {}),
]
for f, kw in CHAVES_PULO: pulo(f, **kw)
REP['Pular'] = dict(quadros=36, segundos=1.5, altura_m=0.40)

# ---------------------------------------------------------------- conferências
def pe_mundo(s): return (rig.matrix_world @ pb[f'foot.{s}'].matrix).translation.copy()
for nome in ('Caminhar', 'Correr'):
    a = bpy.data.actions[nome]; rig.animation_data.action = a; T = int(a.frame_end)
    # deslize: no apoio o pé deve andar para trás em velocidade constante (o chão)
    v = REP[nome]['velocidade_m_s'] / 24; erro = 0.0; alt = 0.0
    for s, fase in (('L', 0), ('R', T // 2)):
        f0 = fase + 1; sc.frame_set(f0); p0 = pe_mundo(s)
        for k in range(1, T // 2 - 2):
            sc.frame_set(f0 + k); p = pe_mundo(s)
            erro = max(erro, abs((p - p0).y - v * k), abs((p - p0).z))
    REP[nome]['pe_no_apoio_erro_mm'] = round(erro * 1000, 1)
    alc = 0.0                                       # o IK alcança o controle? (perna esticada demais deixa o pé para trás)
    for f in range(T + 1):
        sc.frame_set(f)
        for s in 'LR': alc = max(alc, ((rig.matrix_world @ pb[f'foot.{s}'].matrix).translation - (rig.matrix_world @ pb[f'pe_ik.{s}'].matrix).translation).length)
    REP[nome]['pe_longe_do_controle_mm'] = round(alc * 1000, 1)
    sc.frame_set(0); q0 = [x.copy() for x in (pb['hips'].location, pb['pe_ik.L'].location)]; sc.frame_set(T)
    REP[nome]['loop_fecha'] = all((a_ - b_).length < 1e-5 for a_, b_ in zip(q0, (pb['hips'].location, pb['pe_ik.L'].location)))
a = bpy.data.actions['Pular']; rig.animation_data.action = a
alt = []
for f in range(0, 37):
    sc.frame_set(f); alt.append(round(min(pe_mundo('L').z, pe_mundo('R').z), 3))
REP['Pular']['altura_pe_por_quadro'] = alt
rig.animation_data.action = None; zera(); rig['cabeca_estavel'] = 0.0; sc.frame_set(0)
bpy.ops.wm.save_mainfile()
json.dump(REP, open(REL, 'w'), indent=1, ensure_ascii=False); print('ANIM', json.dumps(REP, ensure_ascii=False))
