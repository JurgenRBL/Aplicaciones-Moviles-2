"""Recursos Lottie originales de Mascotas Perdidas; sin descargas externas."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "assets"


def constant(value):
    return {"a": 0, "k": value}


def tween(values):
    return {"a": 1, "k": [dict(t=t, s=value, **({"e": values[i + 1][1],
        "o": {"x": [0.4], "y": [0]}, "i": {"x": [0.6], "y": [1]}}
        if i + 1 < len(values) else {})) for i, (t, value) in enumerate(values)]}


def shape_layer(index, position, shapes, scale=None, opacity=None):
    return {"ddd": 0, "ind": index, "ty": 4, "nm": f"Forma {index}", "sr": 1,
        "ks": {"o": opacity or constant(100), "r": constant(0), "p": constant(position),
               "a": constant([0, 0, 0]), "s": scale or constant([100, 100, 100])},
        "ao": 0, "shapes": shapes, "ip": 0, "op": 90, "st": 0, "bm": 0}


def ellipse(position, size):
    return {"ty": "el", "p": constant(position), "s": constant(size), "nm": "Almohadilla"}


def fill(color):
    return {"ty": "fl", "c": constant(color), "o": constant(100), "r": 1}


def save(name, width, height, layers):
    data = {"v": "5.7.4", "fr": 30, "ip": 0, "op": 90, "w": width,
        "h": height, "nm": "Mascotas Perdidas - original", "ddd": 0, "assets": [], "layers": layers}
    (ROOT / name).write_text(json.dumps(data), encoding="utf-8")


layers = []
for i, position in enumerate(([60, 87, 0], [165, 55, 0], [270, 87, 0])):
    offset = i * 12
    shapes = [ellipse([0, 10], [42, 33]), ellipse([-24, -17], [17, 23]),
        ellipse([-8, -29], [17, 23]), ellipse([11, -29], [17, 23]),
        ellipse([27, -15], [17, 23]), fill([0.078, 0.42, 0.40, 1] if i != 1 else [0.86, 0.40, 0.30, 1])]
    layers.append(shape_layer(i + 1, position, shapes,
        scale=tween([(0, [80, 80, 100]), (20 + offset, [115, 115, 100]),
                     (50 + offset, [90, 90, 100]), (89, [80, 80, 100])]),
        opacity=tween([(0, [25]), (18 + offset, [100]), (55 + offset, [100]), (89, [25])])))
save("huellitas.json", 330, 145, layers)

layers = []
for i in range(4):
    layers.append(shape_layer(i + 1, [15 + i * 17, 45, 0], [
        {"ty": "rc", "p": constant([0, 0]), "s": constant([10, 48]), "r": constant(5)}, fill([1, 1, 1, 1])],
        scale=tween([(0, [100, 25 + i * 15, 100]), (18 + i * 5, [100, 100, 100]),
                     (55 + i * 5, [100, 30, 100]), (89, [100, 25 + i * 15, 100])])))
save("grabando.json", 85, 90, layers)

confirmation = json.loads((ROOT / "confirmacion.json").read_text(encoding="utf-8"))
for layer in confirmation["layers"]:
    for shape in layer.get("shapes", []):
        if shape.get("ty") == "st":
            shape["c"] = constant([0.078, 0.42, 0.40, 1])
(ROOT / "confirmacion.json").write_text(json.dumps(confirmation), encoding="utf-8")
