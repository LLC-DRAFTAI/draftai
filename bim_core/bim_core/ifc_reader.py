import ifcopenshell
import ifcopenshell.geom
import json
import argparse
import os


def get_space_coordinates(space):
    """Вычисление координат центра помещения"""
    try:
        # Пытаемся получить геометрию через ifcopenshell.geom
        settings = ifcopenshell.geom.settings()
        shape = ifcopenshell.geom.create_shape(settings, space)
        verts = shape.geometry.verts  # список координат вершин (x1,y1,z1, x2,y2,z2, …)

        xs = verts[0::3]
        ys = verts[1::3]
        zs = verts[2::3]

        # Возвращаем центр (среднее по осям)
        return [
            float(sum(xs) / len(xs)),
            float(sum(ys) / len(ys)),
            float(sum(zs) / len(zs)),
        ]
    except Exception:
        # Если не удалось, возвращаем [0,0,0] как заглушку
        return [0.0, 0.0, 0.0]


def export_spaces(ifc_path, out_path):
    model = ifcopenshell.open(ifc_path)

    spaces = []
    for space in model.by_type("IfcSpace"):
        space_id = space.GlobalId
        name = getattr(space, "Name", "") or ""
        longname = getattr(space, "LongName", "") or ""
        description = getattr(space, "Description", "") or ""

        # Приоритет: LongName → Name → Description
        display_name = longname or name or description or f"Space_{space_id}"

        coords = get_space_coordinates(space)

        # Получаем этаж (если привязан)
        storey = None
        try:
            rel = space.Decomposes[0].RelatingObject
            if rel.is_a("IfcBuildingStorey"):
                storey = rel.Name
        except Exception:
            storey = None

        spaces.append(
            {
                "id": space_id,
                "name": display_name,
                "storey": storey,
                "coordinates": coords,
            }
        )

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"spaces": spaces}, f, ensure_ascii=False, indent=2)

    print(f"✅ Успешно сохранено {len(spaces)} помещений в {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ifc", required=True, help="Путь к IFC файлу")
    parser.add_argument("--out", required=True, help="Путь для сохранения spaces.json")
    args = parser.parse_args()

    export_spaces(args.ifc, args.out)
