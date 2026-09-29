"""
3D model recepce – SOUČASNÝ STAV (podle fotek).

Spuštění:
  • v Blenderu: záložka Scripting → Open → tento soubor → Run Script
  • z příkazové řádky: blender --background --python recepce_soucasny_stav.py -- --render
    (nebo s knihovnou bpy: python recepce_soucasny_stav.py --render)

Všechny rozměry jsou v metrech a jsou ODHADNUTÉ z fotek. Nejdůležitější
rozměry jsou nahoře v sekci ROZMĚRY – po přeměření stačí přepsat čísla
a skript spustit znovu.

Souřadnice (pohled shora):
  osa X = šířka recepce (0 = stěna se skříňkami, vpravo příčka ke chodbě)
  osa Y = hloubka recepce (0 = otevřená strana do haly, kladně k oknu)
  osa Z = výška
"""

import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

# ---------------------------------------------------------------- ROZMĚRY ---
VYSKA_STROPU = 2.70

RECEPCE_SIRKA = 2.80        # vnitřní šířka recepce (X)
RECEPCE_HLOUBKA = 4.60      # od hrany haly k oknu (Y)

OKNO_OD_LEVE_STENY = 0.35   # levá hrana okenního otvoru
OKNO_SIRKA = 2.00
OKNO_PARAPET = 0.90         # výška parapetu
OKNO_VYSKA = 1.35

SKRINKY_DELKA = 3.20        # dvě nízké skříňky dohromady
SKRINKY_HLOUBKA = 0.45
SKRINKY_VYSKA = 0.95

PULT_OD_LEVE_STENY = 1.05   # levý konec recepčního pultu
PULT_Y = 3.25               # přední (návštěvnická) strana pultu
PULT_VYSKA = 1.12

HALA_HLOUBKA = 2.30         # šířka vstupní chodby / haly
VSTUP_DELKA = 5.50          # od recepce ke vstupním dveřím
CHODBA_SIRKA = 1.55         # chodba k ordinacím/kancelářím
CHODBA_DELKA = 12.0

# ---------------------------------------------------------------- POMOCNÉ ---
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def reset_scene():
    """Smaže vše ze scény (lze tak skript spouštět opakovaně)."""
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights,
                 bpy.data.cameras, bpy.data.collections, bpy.data.worlds):
        for item in list(coll):
            coll.remove(item)


def collection(name, parent=None):
    col = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(col)
    return col


def material(name, color, rough=0.6, metal=0.0, alpha=1.0, transmission=0.0,
             emission=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Alpha"].default_value = alpha
    p.inputs["Transmission Weight"].default_value = transmission
    if emission:
        p.inputs["Emission Color"].default_value = (*emission, 1)
        p.inputs["Emission Strength"].default_value = strength
    m.diffuse_color = (*color, alpha)
    return m


def textured(name, c1, c2, kind="wood", scale=8.0, rough=0.55):
    """Jednoduchá procedurální textura – dřevo (dub) nebo koberec."""
    m = material(name, c1, rough)
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    if kind == "wood":
        mp.inputs["Scale"].default_value = (1.0, 1.0, 25.0)
        tex = nt.nodes.new("ShaderNodeTexWave")
        tex.wave_type = "BANDS"
        tex.bands_direction = "Z"
        tex.inputs["Scale"].default_value = scale
        tex.inputs["Distortion"].default_value = 6.0
        tex.inputs["Detail"].default_value = 3.0
    else:
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = scale
        tex.inputs["Detail"].default_value = 12.0
    nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*c1, 1)
    ramp.color_ramp.elements[1].color = (*c2, 1)
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    if kind != "wood":
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.25
        nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    return m


def link(obj, col):
    for c in obj.users_collection:
        c.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def box(name, x0, x1, y0, y1, z0, z1, mat, col, bevel=0.0):
    """Kvádr zadaný rozsahy souřadnic."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    obj.location = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    obj.scale = (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))
    obj.data.materials.append(mat)
    if bevel:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.transform_apply(scale=True)
        obj.select_set(False)
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 3
    return obj


def cylinder(name, loc, r, h, mat, col, verts=48, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h,
                                        location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return link(obj, col)


def rod(name, p0, p1, r, mat, col):
    """Válec mezi dvěma body (nohy židlí, stolů)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    obj = cylinder(name, (p0 + p1) / 2, r, d.length, mat, col, verts=16)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = d.to_track_quat("Z", "Y")
    return obj


def parent_group(name, objs, col, loc=(0, 0, 0), rot_z=0.0):
    empty = bpy.data.objects.new(name, None)
    col.objects.link(empty)
    for o in objs:
        o.parent = empty
    empty.location = loc
    empty.rotation_euler = (0, 0, math.radians(rot_z))
    return empty


# -------------------------------------------------------------- MATERIÁLY ---
def make_materials():
    return {
        "zed": material("Zeď – bílá", (0.86, 0.86, 0.83), 0.9),
        "strop": material("Strop – bílý", (0.9, 0.9, 0.88), 0.9),
        "sokl": material("Sokl – šedý", (0.45, 0.43, 0.4), 0.7),
        "koberec": textured("Koberec – šedohnědý", (0.20, 0.17, 0.15),
                            (0.33, 0.29, 0.26), "noise", 400.0, 0.95),
        "dub": textured("Dub – světlý dekor", (0.45, 0.31, 0.19),
                        (0.62, 0.46, 0.30), "wood", 6.0, 0.5),
        "orech": textured("Skříň – ořech", (0.22, 0.09, 0.04),
                          (0.32, 0.14, 0.06), "wood", 5.0, 0.5),
        "antracit": material("Antracit – lamino", (0.035, 0.035, 0.04), 0.55),
        "kov_cerny": material("Kov – černý mat", (0.02, 0.02, 0.02), 0.4, 0.6),
        "kov_chrom": material("Kov – chrom", (0.8, 0.8, 0.8), 0.15, 1.0),
        "latka": material("Látka – černá", (0.03, 0.03, 0.032), 0.95),
        "latka_modra": material("Látka – modrá", (0.03, 0.08, 0.25), 0.9),
        "plast_bily": material("Plast – okna", (0.92, 0.92, 0.9), 0.35),
        "sklo": material("Sklo", (0.8, 0.9, 0.95), 0.02, 0, 1.0, 1.0),
        "sklo_mlecne": material("Sklo – mléčné", (0.9, 0.92, 0.93), 0.35,
                                0, 1.0, 0.6),
        "ram_dveri": material("Rám dveří – antracit", (0.05, 0.05, 0.06), 0.4),
        "dvere_bile": material("Dveře – bílé", (0.9, 0.9, 0.88), 0.5),
        "radiator": material("Radiátor – bílý", (0.88, 0.88, 0.86), 0.35),
        "klima": material("Klimatizace – béžová", (0.80, 0.74, 0.60), 0.5),
        "karton": material("Karton", (0.55, 0.40, 0.24), 0.9),
        "cervena": material("Hydrant – červený", (0.65, 0.02, 0.02), 0.25),
        "svetlo": material("Svítidlo – panel", (1, 1, 1), 0.4, 0, 1, 0,
                           (1.0, 0.97, 0.92), 6.0),
        "papir": material("Papír / časopisy", (0.85, 0.7, 0.6), 0.6),
        "venku": material("Venku – obloha", (0.7, 0.82, 0.95), 1, 0, 1, 0,
                          (0.75, 0.85, 1.0), 3.0),
    }


# ----------------------------------------------------------------- STAVBA ---
def build_shell(M, col, ceil_col):
    H = VYSKA_STROPU
    W, D = RECEPCE_SIRKA, RECEPCE_HLOUBKA
    t = 0.15      # příčky
    tw = 0.35     # obvodová zeď s oknem
    hy = -HALA_HLOUBKA + 0.9   # jižní stěna haly (hala mezi hy a 0.9)
    xL = -VSTUP_DELKA           # vstupní dveře
    cx0, cx1 = W + t, W + t + CHODBA_SIRKA   # chodba k ordinacím

    # podlaha (koberec všude)
    box("Podlaha", xL, cx1 + t, hy - t, CHODBA_DELKA, -0.02, 0, M["koberec"], col)

    # --- recepce
    # levá stěna se skříňkami (od rohu u šatní skříně k oknu)
    box("Stěna levá", -t, 0, 0.9, D, 0, H, M["zed"], col)
    # pravá příčka mezi recepcí a chodbou
    box("Příčka ke chodbě", W, W + t, 0, D, 0, H, M["zed"], col)
    # okenní stěna s otvorem
    ox0 = OKNO_OD_LEVE_STENY
    ox1 = ox0 + OKNO_SIRKA
    oz0, oz1 = OKNO_PARAPET, OKNO_PARAPET + OKNO_VYSKA
    y0, y1 = D, D + tw
    box("Okenní stěna L", -t, ox0, y0, y1, 0, H, M["zed"], col)
    box("Okenní stěna P", ox1, W + t, y0, y1, 0, H, M["zed"], col)
    box("Okenní stěna pod oknem", ox0, ox1, y0, y1, 0, oz0, M["zed"], col)
    box("Okenní stěna nad oknem", ox0, ox1, y0, y1, oz1, H, M["zed"], col)
    build_window(M, col, ox0, ox1, oz0, oz1, y0, y1)

    # --- hala / vstupní chodba (směr -X ke vstupním dveřím)
    box("Hala – stěna u šatní skříně", xL, -t, 0.9, 0.9 + t, 0, H, M["zed"], col)
    box("Hala – protější stěna", xL, cx1 + t, hy - t, hy, 0, H, M["zed"], col)
    box("Hala – pilastr", -1.1, -0.75, hy, hy + 0.3, 0, H, M["zed"], col, 0.02)
    # podhled (snížený strop) nad vstupní chodbou
    box("Podhled nad vstupem", xL, -0.2, hy, 0.9, H - 0.25, H,
        M["strop"], ceil_col)
    build_entrance(M, col, xL, hy)

    # --- chodba k ordinacím (za pravou příčkou, směr +Y)
    box("Chodba – pravá stěna", cx1, cx1 + t, hy, CHODBA_DELKA, 0, H,
        M["zed"], col)
    box("Chodba – levá stěna za oknem", W, W + t, D, CHODBA_DELKA, 0, H,
        M["zed"], col)
    box("Chodba – čelo", W, cx1 + t, CHODBA_DELKA, CHODBA_DELKA + t, 0, H,
        M["zed"], col)
    for i, yy in enumerate([5.6, 7.4, 9.8]):
        door(M, col, f"Dveře kancelář L{i + 1}", W + t, yy, face=+1)
    for i, yy in enumerate([3.2, 6.8, 9.2]):
        door(M, col, f"Dveře kancelář P{i + 1}", cx1, yy, face=-1)

    # --- stropy
    box("Strop recepce", xL, W + t, 0, D + tw, H, H + 0.1, M["strop"], ceil_col)
    box("Strop hala", xL, cx1 + t, hy - t, 0, H, H + 0.1,
        M["strop"], ceil_col)
    box("Strop chodba", W + t, cx1 + t, 0, CHODBA_DELKA, H, H + 0.1,
        M["strop"], ceil_col)

    # sokly v recepci
    box("Sokl – okno", 0, W, D - 0.01, D, 0, 0.06, M["sokl"], col)
    box("Sokl – příčka", W - 0.01, W, 0, D, 0, 0.06, M["sokl"], col)

    # obloha za oknem
    sky = box("Obloha za oknem", -3, W + 4, D + 3, D + 3.05, -2, 6,
              M["venku"], col)
    sky.visible_shadow = False


def build_window(M, col, x0, x1, z0, z1, y0, y1):
    fy = y0 + 0.12           # rovina rámu
    f = 0.07                 # šířka profilu
    d = 0.08
    # parapet (vnitřní)
    box("Parapet", x0 - 0.05, x1 + 0.05, y0 - 0.04, fy, z0 - 0.03, z0,
        M["plast_bily"], col)
    # obvodový rám
    box("Rám okna dole", x0, x1, fy, fy + d, z0, z0 + f, M["plast_bily"], col)
    box("Rám okna nahoře", x0, x1, fy, fy + d, z1 - f, z1, M["plast_bily"], col)
    box("Rám okna vlevo", x0, x0 + f, fy, fy + d, z0, z1, M["plast_bily"], col)
    box("Rám okna vpravo", x1 - f, x1, fy, fy + d, z0, z1, M["plast_bily"], col)
    # tři křídla (jako na fotce – prostřední otevíravé)
    w = (x1 - x0) / 3
    for i in (1, 2):
        xx = x0 + i * w
        box(f"Sloupek okna {i}", xx - f / 2, xx + f / 2, fy, fy + d, z0, z1,
            M["plast_bily"], col)
    box("Sklo okna", x0 + f, x1 - f, fy + 0.035, fy + 0.045, z0 + f, z1 - f,
        M["sklo"], col)
    # žaluzie nahoře (stažené)
    box("Žaluzie – kazeta", x0 + f, x1 - f, fy - 0.03, fy, z1 - f - 0.05,
        z1 - f, M["ram_dveri"], col)
    # kliky
    box("Klika okna", x0 + w + 0.05, x0 + w + 0.07, fy - 0.04, fy,
        (z0 + z1) / 2 - 0.06, (z0 + z1) / 2 + 0.06, M["plast_bily"], col)


def build_entrance(M, col, xL, hy):
    """Prosklené vstupní dveře s bočním světlíkem na konci chodby."""
    yc = hy + 0.95
    fx = xL + 0.02
    fr = 0.06
    x0, x1 = fx, fx + 0.06
    box("Vstup – rám L", x0, x1, yc - 0.55, yc - 0.55 + fr, 0, 2.2,
        M["ram_dveri"], col)
    box("Vstup – rám středový", x0, x1, yc + 0.45, yc + 0.45 + fr, 0, 2.2,
        M["ram_dveri"], col)
    box("Vstup – rám P", x0, x1, yc + 0.8 - fr, yc + 0.8, 0, 2.2,
        M["ram_dveri"], col)
    box("Vstup – nadpraží", x0, x1, yc - 0.55, yc + 0.8, 2.2 - fr, 2.2,
        M["ram_dveri"], col)
    box("Vstup – sklo dveří", x0 + 0.02, x0 + 0.03, yc - 0.49, yc + 0.45,
        0, 2.14, M["sklo_mlecne"], col)
    box("Vstup – sklo světlíku", x0 + 0.02, x0 + 0.03, yc + 0.51, yc + 0.74,
        0, 2.14, M["sklo_mlecne"], col)
    box("Vstup – klika", x0 + 0.06, x0 + 0.08, yc + 0.28, yc + 0.4, 1.02, 1.05,
        M["kov_chrom"], col)
    box("Vstup – zavírač", x0 + 0.06, x0 + 0.12, yc - 0.4, yc - 0.05, 2.08,
        2.14, M["ram_dveri"], col)
    # požární hydrant (červený buben) na protější stěně
    cylinder("Hydrant – buben", (-0.3, hy + 0.1, 1.25), 0.33, 0.14,
             M["cervena"], col, rot=(math.radians(90), 0, 0))


def door(M, col, name, x_wall, yc, face=+1):
    """Bílé dveře do kanceláře v chodbě (face = směr do chodby po ose X)."""
    x0 = x_wall if face > 0 else x_wall - 0.04
    box(name, x0, x0 + 0.04, yc - 0.42, yc + 0.42, 0, 2.0,
        M["dvere_bile"], col)
    box(name + " – zárubeň", x0 - 0.005, x0 + 0.045, yc - 0.46, yc + 0.46,
        2.0, 2.04, M["dvere_bile"], col)
    hx = x0 + (0.06 if face > 0 else -0.02)
    box(name + " – klika", hx - 0.02, hx, yc + 0.3, yc + 0.36, 1.0, 1.03,
        M["kov_chrom"], col)


# ---------------------------------------------------------------- NÁBYTEK ---
def sideboard(M, col, name, x0, y0, length):
    """Nízká skříňka: antracitový korpus, dubová dvířka, černé úchytky."""
    dpt, h = SKRINKY_HLOUBKA, SKRINKY_VYSKA
    objs = [
        box(name + " – korpus", 0, dpt, 0, length, 0.02, h - 0.025,
            M["antracit"], col),
        box(name + " – deska", 0, dpt + 0.01, 0, length, h - 0.025, h,
            M["antracit"], col, 0.003),
        box(name + " – sokl", 0.03, dpt - 0.03, 0.03, length - 0.03, 0, 0.02,
            M["antracit"], col),
    ]
    half = (length - 0.08) / 2
    for i in range(2):
        yy = 0.04 + i * (half + 0.0)
        objs.append(box(f"{name} – dvířka {i + 1}", dpt, dpt + 0.02, yy,
                        yy + half - 0.004, 0.06, h - 0.06, M["dub"], col, 0.002))
    # úchytky
    objs.append(box(name + " – úchytka 1", dpt + 0.02, dpt + 0.035,
                    0.04 + half - 0.05, 0.04 + half - 0.04, h - 0.3, h - 0.14,
                    M["kov_cerny"], col))
    objs.append(cylinder(name + " – zámek", (dpt + 0.025, 0.04 + half - 0.15,
                                             h - 0.12), 0.012, 0.02,
                         M["kov_chrom"], col, rot=(0, math.radians(90), 0)))
    return parent_group(name, objs, col, (x0, y0, 0))


def wardrobe(M, col):
    """Vysoká šatní skříň v hale (ořech + černý bok), čelem do haly."""
    x0, x1, y0, y1, h = -1.35, -0.1, 0.42, 0.9, 2.05
    box("Šatní skříň – korpus", x0, x1, y0 + 0.02, y1, 0, h - 0.03,
        M["antracit"], col)
    box("Šatní skříň – horní deska", x0, x1, y0, y1, h - 0.03, h,
        M["orech"], col, 0.003)
    n = 3
    w = (x1 - x0 - 0.02) / n
    for i in range(n):
        xx = x0 + 0.01 + i * w
        box(f"Šatní skříň – dveře {i + 1}", xx + 0.002, xx + w - 0.002,
            y0, y0 + 0.02, 0.03, h - 0.035, M["orech"], col, 0.002)


def reception_desk(M, col):
    """Recepční pult: antracitový čelní panel + dubová horní deska,
    za ním pracovní stůl (dub, černá kovová podnož) a kancelářská židle."""
    x0, x1 = PULT_OD_LEVE_STENY, RECEPCE_SIRKA - 0.02
    y = PULT_Y
    h = PULT_VYSKA
    xm = x0 + (x1 - x0) * 0.62
    # dvě části čelního panelu (na fotce je vidět spára)
    box("Pult – čelo 1", x0, xm - 0.002, y, y + 0.04, 0, h - 0.03,
        M["antracit"], col)
    box("Pult – čelo 2", xm + 0.002, x1, y, y + 0.04, 0, h - 0.03,
        M["antracit"], col)
    box("Pult – levý bok", x0, x0 + 0.03, y, y + 0.32, 0, h - 0.03,
        M["antracit"], col)
    box("Pult – horní deska 1", x0 - 0.02, xm - 0.002, y - 0.03, y + 0.32,
        h - 0.03, h, M["dub"], col, 0.004)
    box("Pult – horní deska 2", xm + 0.002, x1, y - 0.03, y + 0.32,
        h - 0.03, h, M["dub"], col, 0.004)
    # sešívačka + papírek na pultu
    box("Sešívačka", x0 + 0.35, x0 + 0.52, y + 0.1, y + 0.15, h, h + 0.06,
        M["kov_cerny"], col, 0.01)
    box("Lísteček", x0 + 0.9, x0 + 1.0, y + 0.08, y + 0.16, h, h + 0.002,
        M["papir"], col)

    # pracovní stůl za pultem
    dx0, dx1 = x0 - 0.05, x0 + 1.35
    dy0, dy1 = y + 0.36, y + 1.06
    dh = 0.75
    box("Stůl – deska", dx0, dx1, dy0, dy1, dh - 0.025, dh, M["dub"], col,
        0.003)
    for i, (lx, ly) in enumerate([(dx0 + 0.03, dy0 + 0.03), (dx1 - 0.06, dy0 + 0.03),
                                  (dx0 + 0.03, dy1 - 0.06), (dx1 - 0.06, dy1 - 0.06)]):
        box(f"Stůl – noha {i + 1}", lx, lx + 0.03, ly, ly + 0.03, 0,
            dh - 0.025, M["kov_cerny"], col)
    box("Stůl – rám", dx0 + 0.03, dx1 - 0.03, dy0 + 0.03, dy0 + 0.05,
        dh - 0.1, dh - 0.025, M["kov_cerny"], col)
    box("Stůl – rám zadní", dx0 + 0.03, dx1 - 0.03, dy1 - 0.05, dy1 - 0.03,
        dh - 0.1, dh - 0.025, M["kov_cerny"], col)
    box("Monitor", dx0 + 0.55, dx0 + 1.05, dy0 + 0.35, dy0 + 0.37,
        dh + 0.1, dh + 0.42, M["antracit"], col, 0.005)
    box("Monitor – stojan", dx0 + 0.77, dx0 + 0.83, dy0 + 0.37, dy0 + 0.45,
        dh, dh + 0.15, M["kov_cerny"], col)
    box("Papíry na stole", dx0 + 0.1, dx0 + 0.4, dy0 + 0.05, dy0 + 0.3,
        dh, dh + 0.01, M["papir"], col)
    office_chair(M, col, (x0 + 0.75, y + 1.35), 180)


def office_chair(M, col, xy, rot):
    objs = []
    hub = (0, 0, 0.08)
    for i in range(5):
        a = math.radians(i * 72)
        objs.append(rod(f"Kanc. židle – rameno {i}", hub,
                        (0.3 * math.cos(a), 0.3 * math.sin(a), 0.05), 0.015,
                        M["kov_cerny"], col))
        objs.append(cylinder(f"Kanc. židle – kolečko {i}",
                             (0.3 * math.cos(a), 0.3 * math.sin(a), 0.03),
                             0.03, 0.03, M["kov_cerny"], col,
                             rot=(math.radians(90), 0, a)))
    objs.append(cylinder("Kanc. židle – píst", (0, 0, 0.26), 0.025, 0.36,
                         M["kov_chrom"], col))
    objs.append(box("Kanc. židle – sedák", -0.23, 0.23, -0.23, 0.23, 0.44,
                    0.51, M["latka_modra"], col, 0.03))
    objs.append(box("Kanc. židle – opěrák", -0.21, 0.21, 0.2, 0.25, 0.58,
                    1.0, M["latka_modra"], col, 0.03))
    objs.append(box("Kanc. židle – držák", -0.03, 0.03, 0.17, 0.2, 0.46,
                    0.62, M["kov_cerny"], col))
    return parent_group("Kancelářská židle", objs, col, (*xy, 0), rot)


def chair_shell(name, mat, col, r=0.27, seg=24):
    """Oblouková skořepina opěradla: uprostřed vyšší, k područkám klesá."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bottom, top = [], []
    for i in range(seg + 1):
        a = math.radians(-120 + 240 * i / seg)
        x, y = r * math.sin(a), r * math.cos(a) - 0.02
        k = abs(a) / math.radians(120)
        zt = 0.84 - 0.24 * k ** 1.6
        bottom.append(bm.verts.new((x, y, 0.40)))
        top.append(bm.verts.new((x, y, zt)))
    for i in range(seg):
        bm.faces.new((bottom[i], bottom[i + 1], top[i + 1], top[i]))
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    obj.data.materials.append(mat)
    sol = obj.modifiers.new("Tloušťka", "SOLIDIFY")
    sol.thickness = 0.08
    sol.offset = 0
    sub = obj.modifiers.new("Zaoblení", "SUBSURF")
    sub.levels = sub.render_levels = 2
    for poly in mesh.polygons:
        poly.use_smooth = True
    return obj


def lounge_chair(M, col, name, xy, rot):
    """Černé čalouněné křeslo s prošívaným opěrákem na 4 šikmých nohách."""
    objs = []
    # 4 nohy (paprsky do X)
    for i in range(4):
        a = math.radians(45 + i * 90)
        objs.append(rod(f"{name} – noha {i}", (0, 0, 0.3),
                        (0.33 * math.cos(a), 0.33 * math.sin(a), 0.0), 0.018,
                        M["kov_cerny"], col))
    objs.append(cylinder(name + " – hlava", (0, 0, 0.32), 0.07, 0.06,
                         M["kov_cerny"], col))
    # sedák
    objs.append(box(name + " – sedák", -0.26, 0.26, -0.24, 0.22, 0.35, 0.47,
                    M["latka"], col, 0.04))
    # zaoblené skořepinové opěradlo (prošívané, s područkami)
    objs.append(chair_shell(name + " – opěrák", M["latka"], col))
    return parent_group(name, objs, col, (*xy, 0), rot)


def coffee_table(M, col, xy):
    r, h = 0.30, 0.50
    objs = [cylinder("Konferenční stolek – deska", (0, 0, h - 0.0125), r,
                     0.025, M["dub"], col, 64)]
    for i in range(3):
        a = math.radians(90 + i * 120)
        objs.append(rod(f"Konferenční stolek – noha {i}",
                        (0.16 * math.cos(a), 0.16 * math.sin(a), h - 0.025),
                        (0.2 * math.cos(a), 0.2 * math.sin(a), 0), 0.014,
                        M["kov_cerny"], col))
    for i in range(4):   # časopisy
        m = box(f"Časopis {i + 1}", -0.1, 0.1, -0.14, 0.14, h,
                h + 0.006, M["papir"], col)
        m.location = (0.05 + i * 0.03, 0.05 - i * 0.02, h + 0.004 * i + 0.003)
        m.rotation_euler = (0, 0, math.radians(20 + i * 9))
        objs.append(m)
    return parent_group("Konferenční stolek", objs, col, (*xy, 0))


def radiator(M, col, x0, x1, y):
    n = int((x1 - x0) / 0.06)
    for i in range(n):
        xx = x0 + i * 0.06
        box(f"Radiátor – článek {i + 1:02d}", xx, xx + 0.045, y - 0.16,
            y - 0.05, 0.15, 0.75, M["radiator"], col, 0.01)
    box("Radiátor – přívod", x0 - 0.05, x0, y - 0.12, y - 0.09, 0.05, 0.7,
        M["radiator"], col)


def air_conditioner(M, col, x0, y):
    box("Klimatizace", x0, x0 + 0.9, y - 0.22, y, 2.25, 2.53, M["klima"],
        col, 0.02)
    box("Klimatizace – mřížka", x0 + 0.05, x0 + 0.85, y - 0.225, y - 0.2,
        2.27, 2.33, M["antracit"], col)


def ceiling_light(M, col, name, xy, length=1.2, width=0.3, along="y"):
    x, y = xy
    lx, ly = (width, length) if along == "y" else (length, width)
    H = VYSKA_STROPU
    box(name, x - lx / 2, x + lx / 2, y - ly / 2, y + ly / 2, H - 0.06, H,
        M["plast_bily"], col)
    box(name + " – difuzor", x - lx / 2 + 0.02, x + lx / 2 - 0.02,
        y - ly / 2 + 0.02, y + ly / 2 - 0.02, H - 0.062, H - 0.058,
        M["svetlo"], col)
    bpy.ops.object.light_add(type="AREA", location=(x, y, H - 0.08),
                             rotation=(math.radians(180), 0, 0))
    l = bpy.context.active_object
    l.name = name + " – světlo"
    l.data.shape = "RECTANGLE"
    l.data.size, l.data.size_y = lx, ly
    l.data.energy = 120
    l.data.color = (1.0, 0.96, 0.9)
    link(l, col)


def cardboard_box(M, col, name, xy, rot, size=(0.4, 0.4, 0.62)):
    sx, sy, sz = size
    b = box(name, -sx / 2, sx / 2, -sy / 2, sy / 2, 0, sz, M["karton"], col,
            0.006)
    t = box(name + " – páska", -sx / 2 - 0.001, sx / 2 + 0.001, -0.025, 0.025,
            sz - 0.001, sz + 0.001, M["papir"], col)
    return parent_group(name, [b, t], col, (*xy, 0), rot)


# ------------------------------------------------------------ SVĚTLO, KAMERY
def setup_world_and_render():
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.render.resolution_x = 1200
    sc.render.resolution_y = 1500
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Base Contrast"
    sc.unit_settings.system = "METRIC"
    w = bpy.data.worlds.new("Svět")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (
        0.75, 0.85, 1.0, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    sc.world = w

    # denní světlo oknem
    bpy.ops.object.light_add(type="AREA", location=(
        OKNO_OD_LEVE_STENY + OKNO_SIRKA / 2, RECEPCE_HLOUBKA + 0.45,
        OKNO_PARAPET + OKNO_VYSKA / 2), rotation=(math.radians(90), 0, 0))
    l = bpy.context.active_object
    l.name = "Denní světlo z okna"
    l.data.shape = "RECTANGLE"
    l.data.size, l.data.size_y = OKNO_SIRKA, OKNO_VYSKA
    l.data.energy = 900
    l.data.color = (0.92, 0.96, 1.0)
    bpy.ops.object.light_add(type="SUN", rotation=(
        math.radians(50), 0, math.radians(160)))
    s = bpy.context.active_object
    s.name = "Slunce"
    s.data.energy = 2.5


def camera(name, loc, look_at, lens=16, ortho=None):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam_data.clip_start = 0.05
    if ortho:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = ortho
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    direction = Vector(look_at) - Vector(loc)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return cam


# ------------------------------------------------------------------ MAIN ---
def build():
    reset_scene()
    M = make_materials()
    stavba = collection("Stavba")
    stropy = collection("Stropy", stavba)
    nabytek = collection("Nábytek (současný stav)")
    svetla = collection("Svítidla")

    build_shell(M, stavba, stropy)

    W, D = RECEPCE_SIRKA, RECEPCE_HLOUBKA
    # nábytek recepce
    sideboard(M, nabytek, "Skříňka 1", 0, D - SKRINKY_DELKA, SKRINKY_DELKA / 2)
    sideboard(M, nabytek, "Skříňka 2", 0, D - SKRINKY_DELKA / 2,
              SKRINKY_DELKA / 2)
    reception_desk(M, nabytek)
    coffee_table(M, nabytek, (2.12, 2.55))
    lounge_chair(M, nabytek, "Křeslo 1", (1.48, 2.62), 200)
    lounge_chair(M, nabytek, "Křeslo 2", (2.35, 1.72), -10)
    radiator(M, stavba, OKNO_OD_LEVE_STENY + 0.45, OKNO_OD_LEVE_STENY + 1.45, D)
    air_conditioner(M, stavba, OKNO_OD_LEVE_STENY + OKNO_SIRKA - 0.05, D)
    wardrobe(M, nabytek)
    cardboard_box(M, nabytek, "Krabice (koncentrátor)", (0.3, 0.95), 8)
    box("Odpadkový koš", 2.45, 2.7, D - 0.3, D - 0.05, 0, 0.3,
        M["kov_cerny"], nabytek, 0.01)

    # svítidla
    ceiling_light(M, svetla, "Svítidlo recepce", (1.35, 2.5))
    ceiling_light(M, svetla, "Svítidlo hala", (1.3, -0.7), 0.6, 0.6)
    ceiling_light(M, svetla, "Svítidlo hala u skříně", (-1.6, -0.2), 0.6, 0.6)
    ceiling_light(M, svetla, "Svítidlo vstup", (-3.8, -0.2), 0.6, 0.6)
    for i, yy in enumerate([1.0, 5.0, 9.0]):
        ceiling_light(M, svetla, f"Svítidlo chodba {i + 1}",
                      (W + 0.15 + CHODBA_SIRKA / 2, yy), 0.6, 0.6)

    setup_world_and_render()

    # kamery = pohledy jako na fotkách
    cams = {
        "01_recepce_od_haly": camera("Pohled 1 – recepce od haly (foto 3)",
                                     (1.45, -0.45, 1.55), (1.3, 4.6, 1.0), 14),
        "02_hala_a_vstup": camera("Pohled 2 – hala a vstup (foto 1)",
                                  (2.6, 0.6, 1.6), (-2.0, 0.9, 1.0), 13),
        "03_recepce_a_chodba": camera("Pohled 3 – recepce a chodba (foto 2)",
                                      (-0.6, -1.0, 1.6), (2.4, 4.6, 1.2), 13),
        "04_pudorys": camera("Půdorys (shora)", (W / 2, D / 2 - 0.6, 12),
                             (W / 2, D / 2 - 0.6, 0), ortho=7.5),
        "05_axonometrie": camera("Axonometrie", (1.4, -4.2, 7.5),
                                 (1.4, 2.2, 0.3), 24),
    }
    bpy.context.scene.camera = cams["01_recepce_od_haly"]
    return cams


def render(cams):
    sc = bpy.context.scene
    stropy = [o for o in bpy.data.objects
              if o.name.startswith(("Strop", "Podhled", "Svítidlo"))
              and o.type == "MESH"]
    out = os.path.join(OUT_DIR, "rendery")
    os.makedirs(out, exist_ok=True)
    for key, cam in cams.items():
        top = key in ("04_pudorys", "05_axonometrie")
        for o in stropy:
            o.hide_render = top
        for o in bpy.data.objects:
            if o.type == "LIGHT" and "Svítidlo" in o.name:
                o.data.energy = 40 if top else 120
        if key == "04_pudorys":
            sc.render.resolution_x, sc.render.resolution_y = 1100, 1500
        elif key == "05_axonometrie":
            sc.render.resolution_x, sc.render.resolution_y = 1600, 1200
        else:
            sc.render.resolution_x, sc.render.resolution_y = 1200, 1500
        sc.camera = cam
        sc.render.filepath = os.path.join(out, key + ".png")
        bpy.ops.render.render(write_still=True)
        print("hotovo:", sc.render.filepath)
    for o in stropy:
        o.hide_render = False
    sc.camera = cams["01_recepce_od_haly"]
    sc.render.resolution_x, sc.render.resolution_y = 1200, 1500


if __name__ == "__main__":
    cams = build()
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if "--render" in args:
        render(cams)
    if "--save" in args or "--render" in args:
        bpy.ops.wm.save_as_mainfile(
            filepath=os.path.join(OUT_DIR, "recepce_soucasny_stav.blend"))
