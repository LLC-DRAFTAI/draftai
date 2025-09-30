import json
import re
import sys
from pathlib import Path
import spacy
from pdfminer.high_level import extract_text as extract_pdf_text
import docx

try:
    nlp = spacy.load("ru_core_news_sm")
except OSError:
    print(
        "Модель spaCy 'ru_core_news_sm' не найдена. Установите командой: python -m spacy download ru_core_news_sm"
    )
    sys.exit(1)


def read_text_file(file_path):
    return Path(file_path).read_text(encoding="utf-8")


def read_pdf_file(file_path):
    return extract_pdf_text(file_path)


def read_docx_file(file_path):
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])


def read_input_file(file_path):
    path = Path(file_path)
    if not path.exists():
        print(f"Файл {file_path} не найден!")
        sys.exit(1)
    if file_path.lower().endswith(".txt"):
        return read_text_file(file_path)
    elif file_path.lower().endswith(".pdf"):
        return read_pdf_file(file_path)
    elif file_path.lower().endswith(".docx"):
        return read_docx_file(file_path)
    else:
        print("Поддерживаются только форматы: .txt, .pdf, .docx")
        sys.exit(1)


def extract_parameter(patterns, text, default="Нет данных"):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return default


def extract_entities_with_spacy(text):
    doc = nlp(text)
    entities = {"ORG": [], "PROJECT": [], "LOC": []}
    for ent in doc.ents:
        if ent.label_ in entities:
            entities[ent.label_].append(ent.text)
    return entities


def extract_locations(text):
    loc_entities = []
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "LOC":
            loc_entities.append(ent.text)

    zip_codes = re.findall(r"\b\d{6}\b", text)
    for z in zip_codes:
        if z not in loc_entities:
            loc_entities.append(z)

    coords = re.findall(r"(-?\d{1,3}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)", text)
    for lat, lon in coords:
        coord_str = f"{lat},{lon}"
        if coord_str not in loc_entities:
            loc_entities.append(coord_str)

    return loc_entities if loc_entities else ["Нет данных"]


def extract_heating_system(text):
    boiler_power = extract_parameter(
        [
            r"мощность котла[:\-]?\s*(\d+[.,]?\d*)\s*кВт",
            r"мощность отопительного котла[:\-]?\s*(\d+[.,]?\d*)\s*кВт",
        ],
        text,
    )
    temperature = extract_parameter(
        [
            r"температура[:\-]?\s*(\d+[.,]?\d*(?:/\d+[.,]?\d*)?)\s*°?C?",
            r"температура теплоносителя[:\-]?\s*(\d+[.,]?\d*(?:/\d+[.,]?\d*)?)\s*°?C?",
            r"температура воды[:\-]?\s*(\d+[.,]?\d*(?:/\d+[.,]?\d*)?)\s*°?C?",
            r"температура отопительного контура[:\-]?\s*(\d+[.,]?\d*(?:/\d+[.,]?\d*)?)\s*°?C?",
        ],
        text,
    )
    radiator_type = extract_parameter(
        [r"тип радиаторов[:\-]?\s*(.+)", r"вид радиаторов[:\-]?\s*(.+)"], text
    )
    heat_source = extract_parameter(
        [
            r"источник теплоснабжения[:\-]?\s*(.+)",
            r"теплоснабжение[:\-]?\s*(.+)",
            r"система теплоснабжения[:\-]?\s*(.+)",
        ],
        text,
    )

    heating_system = {
        "system_name": "отопление",
        "boiler_power": boiler_power,
        "radiator_type": radiator_type,
        "temperature": temperature,
        "heat_source": heat_source,
    }
    return heating_system


def extract_rooms(text):
    room_patterns = [
        r"^(?:помещение|комната|зал|офис|наименование помещений)[:\-]?\s*(.+)$",
        r"^\d+\.\s*(.+)$",
        r"^\-\s*(.+)$",
    ]
    matches = []
    for pat in room_patterns:
        matches.extend(re.findall(pat, text, re.IGNORECASE | re.MULTILINE))
    seen = set()
    unique_rooms = []
    for room in matches:
        room_clean = room.strip()
        if room_clean and room_clean not in seen:
            seen.add(room_clean)
            unique_rooms.append(room_clean)
    return unique_rooms if unique_rooms else ["Нет данных"]


def extract_projects(text):
    project_matches = re.findall(
        r"этап[:\-]\s*(.+)|стройка[:\-]\s*(.+)|наименование объекта[:\-]\s*(.+)",
        text,
        re.IGNORECASE,
    )
    projects = []
    for tup in project_matches:
        for val in tup:
            if val:
                val_clean = val.strip()
                if val_clean not in projects:
                    projects.append(val_clean)
    return projects if projects else ["Нет данных"]


def extract_room_temperatures(text):
    results = {}
    patterns = {
        "Офис": r"в\s+офисах?\s+(\d+[.,]?\d*)\s*°?C",
        "Коридор": r"в\s+коридорах?\s+(\d+[.,]?\d*)\s*°?C",
        "Веранда": r"на\s+веранде\s+(\d+[.,]?\d*)\s*°?C",
    }
    for room, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            results[room] = match.group(1)
    return results if results else {"Нет данных": "Нет данных"}


def extract_all_parameters(text):
    data = {}
    data["project_name"] = extract_parameter(
        [r"название проекта[:\-]\s*(.+)", r"проект[:\-]\s*(.+)"], text
    )
    data["object_name"] = extract_parameter([r"объект[:\-]\s*(.+)"], text)

    data["building_area"] = extract_parameter(
        [
            r"площадь здания[:\-]?\s*(\d+[.,]?\d*)\s*(?:м2|м²|кв\.м)",
            r"общая площадь[:\-]?\s*(\d+[.,]?\d*)\s*(?:м2|м²|кв\.м)",
        ],
        text,
    )
    data["floor_area"] = extract_parameter(
        [r"площадь этажа[:\-]?\s*(\d+[.,]?\d*)\s*(?:м2|м²|кв\.м)"], text
    )

    data["levels"] = extract_parameter(
        [
            r"этажность[:\-]?\s*(\d+)",
            r"этажей[:\-]?\s*(\d+)",
            r"количество этажей[:\-]?\s*(\d+)",
        ],
        text,
    )

    spacy_entities = extract_entities_with_spacy(text)
    data["ORG"] = spacy_entities.get("ORG", [])
    data["PROJECT"] = extract_projects(text)
    data["LOC"] = extract_locations(text)

    data["heating_system"] = extract_heating_system(text)
    data["rooms"] = extract_rooms(text)
    data["room_temperatures"] = extract_room_temperatures(text)

    return data


def main(input_file, output_file):
    text = read_input_file(input_file)
    extracted_data = extract_all_parameters(text)
    output_path = Path(output_file)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=4)
    print(f"Данные успешно сохранены в {output_file}")
    print(json.dumps(extracted_data, ensure_ascii=False, indent=4))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Использование: python -m nlp_core.run <input_file> <output_json_file>")
        sys.exit(1)
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    main(input_file, output_file)
