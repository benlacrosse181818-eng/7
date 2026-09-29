# Recepce – 3D model v Blenderu (současný stav)

| Soubor | Co to je |
|---|---|
| `recepce_soucasny_stav.blend` | hotová scéna – otevři v Blenderu (4.2+) |
| `recepce_soucasny_stav.py` | skript, který scénu postaví (všechny rozměry nahoře v sekci ROZMĚRY) |
| `rendery/` | pohledy: od haly, hala se vstupem, recepce s chodbou, půdorys, axonometrie |

## Rozměry (odhad z fotek – je potřeba přeměřit)

- recepce 2,80 × 4,60 m, strop 2,70 m
- okno 2,00 × 1,35 m, parapet 0,90 m
- 2 nízké skříňky 2× 1,60 m, hloubka 0,45 m, výška 0,95 m
- recepční pult: výška 1,12 m, od levé stěny 1,05 m k pravé příčce
- konferenční stolek Ø 60 cm, 2 křesla, šatní skříň v hale, krabice

Po přeměření stačí přepsat čísla v sekci `ROZMĚRY` a spustit znovu:

```
blender --background --python recepce_soucasny_stav.py -- --render
```

(v Blenderu: Scripting → Open → Run Script; `--save` jen uloží .blend bez renderu)

## Scéna v Blenderu

Kolekce: **Stavba** (zdi, okno, radiátor, klimatizace, dveře), **Stropy**,
**Nábytek (současný stav)** – každý kus je samostatný objekt/skupina, takže
se dá snadno posouvat, mazat nebo nahradit – a **Svítidla**.
Kamery: Pohled 1–3 (odpovídají fotkám), Půdorys, Axonometrie.
