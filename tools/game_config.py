#!/usr/bin/env python3
"""Validate balance settings, resolve stadium overrides, and prepare Flash builds."""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "resources/game_config.json"
CLASSES = tuple("CRA ECAFLIP ENIRIPSA ENUTROF FECA IOP OSAMODAS PANDAWA ROUBLARD SACRIEUR SADIDA SRAM XELOR ZOBAL".split())
STADIUMS = tuple("FARMSTEAD BRAKMAR BEACH BONTA FRIGOST KARA FOREST BALLOTIN PIXEL".split())


class ConfigError(ValueError):
    pass


def validate(value, schema, path="config"):
    """Dependency-free validator for the constraints used in our bundled schema."""
    kind = schema["type"]
    valid = {
        "object": isinstance(value, dict), "string": isinstance(value, str),
        "boolean": isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
    }[kind]
    if not valid:
        raise ConfigError(f"{path}: expected {kind}")
    if kind == "object":
        properties = schema["properties"]
        unknown = value.keys() - properties.keys()
        missing = set(schema.get("required", [])) - value.keys()
        if unknown or missing:
            raise ConfigError(f"{path}: unknown keys {sorted(unknown)}, missing keys {sorted(missing)}")
        for key, child in value.items():
            validate(child, properties[key], f"{path}.{key}")
    if kind in ("number", "integer"):
        if not math.isfinite(value):
            raise ConfigError(f"{path}: must be finite")
        for bound, comparison in (("minimum", lambda a, b: a >= b),
                                  ("maximum", lambda a, b: a <= b),
                                  ("exclusiveMinimum", lambda a, b: a > b)):
            if bound in schema and not comparison(value, schema[bound]):
                raise ConfigError(f"{path}: requires {bound} {schema[bound]}")
    if "enum" in schema and value not in schema["enum"]:
        raise ConfigError(f"{path}: expected one of {schema['enum']}")
    if kind == "string" and len(value) < schema.get("minLength", 0):
        raise ConfigError(f"{path}: cannot be empty")


def merge(base, overrides):
    result = deepcopy(base)
    for key, value in overrides.items():
        result[key] = merge(result[key], value) if isinstance(value, dict) else deepcopy(value)
    return result


def resolve_stadium(config, stadium):
    if stadium not in config["stadiums"]:
        raise ConfigError(f"Unknown stadium: {stadium}")
    return merge(config["rules"], config["stadiums"][stadium]["overrides"])


def check_rules(rules, path):
    match = rules["match"]
    if match["turns_per_period"] > match["turns_per_match"]:
        raise ConfigError(f"{path}: turns_per_period exceeds turns_per_match")
    simulation = rules["simulation"]["simulation"]
    if simulation["probability_min"] > simulation["probability_max"]:
        raise ConfigError(f"{path}: probability_min exceeds probability_max")


def load_config(path=DEFAULT_CONFIG):
    try:
        config = json.loads(Path(path).read_text())
    except (OSError, ValueError) as error:
        raise ConfigError(f"Cannot load {path}: {error}") from error
    schema = json.loads((ROOT / "resources/game_config.schema.json").read_text())
    validate(config, schema)
    check_rules(config["rules"], "rules")
    for stadium in STADIUMS:
        check_rules(resolve_stadium(config, stadium), stadium)
    if not any(s["enabled"] for s in config["stadiums"].values()):
        raise ConfigError("At least one stadium must be enabled")
    return config


def apply_resources(directory, config):
    """Update legacy client settings in a staging directory, preserving asset URLs."""
    directory = Path(directory)
    path = directory / "config.json"
    legacy = json.loads(path.read_text())
    general = config["general"]
    legacy["server"] = {"host": general["server"]["host"], "port": str(general["server"]["port"])}
    for new, old in (("scene_3d", "3dActivated"), ("show_stats", "showStats"),
                     ("premium_customization_enabled", "premiumServiceEnabled")):
        legacy[old] = str(general[new]).lower()
    legacy["sound"]["enabled"] = str(general["sound"]["enabled"]).lower()
    legacy["sound"]["masterVolume"] = str(general["sound"]["master_volume"])
    match = config["rules"]["match"]
    legacy["chrono"]["placementDuration"] = str(match["placement_seconds"])
    legacy["chrono"]["firstTurnDuration"] = str(match["planning_seconds"])
    legacy["chrono"]["turnDuration"] = str(match["planning_seconds"])
    path.write_text(json.dumps(legacy, indent=2) + "\n")
    stadium_path = directory / "stadiums.json"
    if stadium_path.exists():
        stadiums = json.loads(stadium_path.read_text())
        for stadium in stadiums["stadiums"].values():
            if not (ROOT / "assets/models/stadiums" / stadium["path"]).exists():
                stadium["path"] = stadiums["stadiums"]["FARMSTEAD"]["path"]
        stadium_path.write_text(json.dumps(stadiums, indent=2) + "\n")
    lang_path = directory / "lang.json"
    if lang_path.exists():
        text = lang_path.read_text(encoding="utf-8-sig")
        translations = {
            "en": "Free local league. Play CPU matches during the event. Wins and draws add points; defeats do not eliminate you. Results and rankings are saved.",
            "fr": "Ligue locale gratuite. Jouez contre l'ordinateur pendant l'événement. Les victoires et les matchs nuls rapportent des points ; une défaite ne vous élimine pas. Les résultats sont sauvegardés.",
            "de": "Kostenlose lokale Liga. Spiele während des Events gegen den Computer. Siege und Unentschieden bringen Punkte; Niederlagen führen nicht zum Ausscheiden. Ergebnisse werden gespeichert.",
            "es": "Liga local gratuita. Juega contra el ordenador durante el evento. Las victorias y los empates suman puntos; las derrotas no te eliminan. Los resultados se guardan.",
        }
        for key in ("tournament_help_content", "tournament_elimination_rule"):
            block = json.dumps(translations, ensure_ascii=False, indent=4).replace("\n", "\n    ")
            pattern = r'("' + key + r'"\s*:\s*)\{.*?\n    \}'
            text, count = re.subn(pattern, lambda match: match[1] + block, text, count=1, flags=re.S)
            if count != 1:
                raise ConfigError(f"Missing tournament translation block: {key}")
        lang_path.write_text(text)
    (directory / "game_config.json").write_text(json.dumps(config, indent=2) + "\n")


def startup_source(source, config, android=False):
    """Compile configured preview attributes and client-supported rules into AS3."""
    source = str(source)
    lines = []
    attributes = config["rules"]["classes"]
    for index, name in enumerate(CLASSES, 1):
        values = merge(attributes["defaults"], attributes["overrides"].get(name, {}))
        args = ",".join(str(values[k]) for k in ("earth", "air", "fire", "water", "health", "regeneration"))
        lines.append(f"         if(classId == {index}) return new BoufbowlerAttributesModel({args});")
    helper = "\n      private static function configuredAttributes(classId:int) : BoufbowlerAttributesModel\n      {\n" + "\n".join(lines) + '\n         throw new Error("Unknown class ID: " + classId);\n      }\n\n'
    helper += "      private static function configuredRole(classId:int) : int\n      {\n"
    for index, name in enumerate(CLASSES, 1):
        role = attributes["overrides"].get(name, {}).get("role", 1 + index % 4)
        helper += f"         if(classId == {index}) return {role};\n"
    helper += '         throw new Error("Unknown class ID: " + classId);\n      }\n\n'
    # Each constructor occurs on one line; use its surrounding model to determine
    # which class owns the preview, rather than sharing mutable attribute objects.
    rewritten = []
    for line in source.splitlines():
        if "new BoufbowlerAttributesModel(12,10,10,10,16,3)" in line:
            if "new ClassAttributesModel" in line:
                class_id = "i"
            elif "hero[1]" in line:
                class_id = "hero[1]"
            elif "galleryRoster" in line:
                class_id = "i+1"
            else:
                class_id = "cls"
            line = line.replace("new BoufbowlerAttributesModel(12,10,10,10,16,3)", f"configuredAttributes({class_id})")
        rewritten.append(line)
    source = "\n".join(rewritten)
    source = re.sub(r"1\s*\+\s*\(?i\s*%\s*4\)?", "configuredRole(i)", source)
    source = re.sub(r"1\s*\+\s*\(?cls\s*%\s*4\)?", "configuredRole(cls)", source)
    source = re.sub(r"1\s*\+\s*\(?hero\[1\]\s*%\s*4\)?", "configuredRole(hero[1])", source)
    source = re.sub(r"1\s*\+\s*\(?\(i\s*\+\s*1\)\s*%\s*4\)?", "configuredRole(i+1)", source)
    source = re.sub(r"1\s*\+\s*\(i\s*\+\s*1\)\s*%\s*4", "configuredRole(i+1)", source)
    marker = "      private static function displayer()"
    if marker not in source or source.count("configuredAttributes(") != 4:
        raise ConfigError("Startup patch layout changed; review configuration injection")
    source = source.replace(marker, helper + marker, 1)
    statements = ["rules.classAttributes = attributes;"]
    match = config["rules"]["match"]
    statements.extend([f"rules.maxBoufbowlerCountPerRole = {match['max_players_per_role']};",
                       f"rules.placementDuration = {match['placement_seconds']};",
                       f"rules.ordersDuration = {match['planning_seconds']};"])
    for key, setter in (("max_distance_factor", "MaxDistanceFactor"), ("earth_distance_bonus", "EarthDistanceBonus"),
                        ("fire_distance_bonus", "FireDistanceBonus"), ("air_distance_bonus", "AirDistanceBonus"),
                        ("water_distance_bonus", "WaterDistanceBonus")):
        statements.append(f"rules.set{setter}({config['rules']['client_ranges'][key]});")
    for index, stadium in enumerate(STADIUMS, 1):
        stadium_match = resolve_stadium(config, stadium)["match"]
        for field, setter in (("turns_per_match", "MaxTurnDuration"), ("turns_per_period", "PeriodTurnDuration"),
                              ("class_ability_uses", "ClassOrderUseByMatch")):
            statements.append(f"rules.set{setter}({index},{stadium_match[field]});")
    source, count = re.subn(r"rules\.classAttributes = attributes;.*?(?=teams = new ArrayList\(\);)",
                           "\n         ".join(statements) + "\n         ", source, count=1, flags=re.S)
    if count != 1:
        raise ConfigError("Could not locate startup rules block")
    source = re.sub(r"stadiums\.addItem\(i,new StadiumItem\(1,0,i\)\);",
                    "if(" + " || ".join(f"i == {i}" for i, name in enumerate(STADIUMS, 1)
                                        if config["stadiums"][name]["enabled"]) +
                    ") stadiums.addItem(i,new StadiumItem(1,0,i));", source)
    from tools.mock_codegen import inject_mock
    from tools.server_codegen import inject_server
    return inject_server(inject_mock(source + "\n", config, android), config, android)


def flashvars_source(source, config):
    old = 'return "en";'
    if source.count(old) != 1:
        raise ConfigError("FlashVarsManager layout changed; review default-language injection")
    return source.replace(old, "return " + json.dumps(config["general"]["language"]) + ";")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--stadium", choices=STADIUMS, help="Print effective rules for a stadium")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        if args.stadium:
            print(json.dumps(resolve_stadium(config, args.stadium), indent=2))
        else:
            print(f"Valid: {args.config} ({config['rules_version']}; {len(STADIUMS)} stadiums)")
    except ConfigError as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
