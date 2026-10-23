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


def validate(value, schema, path="config", definitions=None):
    """Dependency-free validator for the constraints used in our bundled schema."""
    definitions = schema.get("$defs", definitions)
    if "$ref" in schema:
        schema = definitions[schema["$ref"].removeprefix("#/$defs/")]
    kind = schema["type"]
    valid = {
        "object": isinstance(value, dict), "string": isinstance(value, str),
        "array": isinstance(value, list),
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
            validate(child, properties[key], f"{path}.{key}", definitions)
    if kind == "array":
        if not schema.get('minItems', 0) <= len(value) <= schema.get('maxItems', len(value)):
            raise ConfigError(f"{path}: invalid number of items")
        for index, child in enumerate(value):
            validate(child, schema['items'], f"{path}[{index}]", definitions)
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
    from backend.placement import placement_zones
    try:
        placement_zones(2, exclusion=rules["simulation"]["placement"]["ball_exclusion_radius_cells"])
    except ValueError as error:
        raise ConfigError(f"{path}: {error}") from error
    match = rules["match"]
    if match["turns_per_period"] > match["turns_per_match"]:
        raise ConfigError(f"{path}: turns_per_period exceeds turns_per_match")
    simulation = rules["simulation"]["simulation"]
    if simulation["probability_min"] > simulation["probability_max"]:
        raise ConfigError(f"{path}: probability_min exceeds probability_max")
    policy = rules['simulation'].get('rulebook')
    if policy:
        if policy['status']['minimum_ticks'] > policy['status']['base_ticks']:
            raise ConfigError(f'{path}: minimum stun ticks exceed base ticks')
        from backend.rulebook import rulebook_snapshot
        try:
            rulebook_snapshot(rules)
        except ValueError as error:
            raise ConfigError(f'{path}: {error}') from error


def load_config(path=DEFAULT_CONFIG):
    try:
        config = json.loads(Path(path).read_text())
    except (OSError, ValueError) as error:
        raise ConfigError(f"Cannot load {path}: {error}") from error
    schema = json.loads((ROOT / "resources/game_config.schema.json").read_text())
    validate(config, schema)
    progression=config['general'].get('progression')
    if progression:
        leagues=progression['leagues']
        if {l['id'] for l in leagues}!={1,2,3,4,5} or len({l['min_rating'] for l in leagues})!=5 or min(l['min_rating'] for l in leagues)!=0:
            raise ConfigError('League IDs/thresholds must be unique and start at rating zero')
    tournament = config['general']['tournament']
    duration = tournament['end_time'] - tournament['start_time']
    if tournament.get('format')=='elimination' and (tournament['qualification_seconds']+tournament['round_count']*tournament['round_seconds']>duration or tournament['qualifying_top']>2**tournament['round_count']):
        raise ConfigError('Tournament qualification/rounds must fit its duration and bracket capacity')
    if duration <= 0: raise ConfigError('Tournament end_time must follow start_time')
    if tournament.get('repeat_seconds',0) and tournament['repeat_seconds'] < duration:
        raise ConfigError('Repeating tournament entry windows cannot overlap')
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
    from tools.visual_assets import prepare_stadiums, palette_translations
    art_paths = prepare_stadiums(directory.parent)
    stadium_path = directory / "stadiums.json"
    if stadium_path.exists():
        stadiums = json.loads(stadium_path.read_text())
        from tools.stadium_celebrations import celebrations
        goal_celebrations = celebrations(directory.parent)
        for name, stadium in stadiums["stadiums"].items():
            stadium["publicHappyCutsceneName"] = goal_celebrations[name]["animation"]
            stadium["publicHappySound"] = goal_celebrations[name]["sound"]
            if name in art_paths:
                stadium["path"] = art_paths[name]
            if not (ROOT / "assets/models/stadiums" / stadium["path"]).exists():
                stadium["path"] = stadiums["stadiums"]["FARMSTEAD"]["path"]
        stadium_path.write_text(json.dumps(stadiums, indent=2) + "\n")
    lang_path = directory / "lang.json"
    if lang_path.exists():
        from tools.power_descriptions import update_translations
        text = update_translations(palette_translations(lang_path.read_text(encoding="utf-8-sig")), config["rules"])
        translations = {
            "en": "Free tournament league. Only human tournament matchmaking counts. Wins and draws add points; defeats do not eliminate you. CPU games and challenges do not count.",
            "fr": "Ligue gratuite. Seuls les matchs humains via la file du tournoi comptent. Victoires et matchs nuls rapportent des points ; une défaite ne vous élimine pas. Les matchs CPU et les défis ne comptent pas.",
            "de": "Kostenlose Turnierliga. Nur menschliche Spiele aus der Turnierwarteschlange zählen. Siege und Unentschieden bringen Punkte; Niederlagen führen nicht zum Ausscheiden. CPU-Spiele und Herausforderungen zählen nicht.",
            "es": "Liga gratuita. Solo cuentan los partidos humanos de la cola del torneo. Las victorias y los empates suman puntos; las derrotas no te eliminan. Los partidos CPU y los desafíos no cuentan.",
        }
        if config['general']['tournament'].get('format')=='elimination':
            top=config['general']['tournament']['qualifying_top']
            translations={
                'en':f'Free qualification: the top {top} players who complete a human tournament match enter the knockout rounds. Bracket opponents are fixed. Draws use qualification seed order; absent players can lose by walkover. Matches already started may finish after entry closes.',
                'fr':f'Qualification gratuite : les {top} premiers ayant terminé un match humain du tournoi accèdent aux tours éliminatoires. Adversaires fixés par le tableau. Un nul est départagé par le classement qualificatif ; absence : forfait possible. Les matchs commencés peuvent finir après la fermeture.',
                'de':f'Kostenlose Qualifikation: Die besten {top} mit einem abgeschlossenen menschlichen Turnierspiel erreichen die K.-o.-Runden. Feste Gegner. Bei Unentschieden zählt die Qualifikation; Abwesenheit kann zum Ausscheiden führen. Begonnene Spiele dürfen nach Anmeldeschluss enden.',
                'es':f'Clasificación gratuita: los {top} mejores que terminen un partido humano del torneo pasan a eliminatorias. Rivales fijos. Empates según clasificación; ausencia puede causar eliminación. Partidos iniciados pueden terminar tras cerrar inscripciones.'}
        from tools.tournament_text import replace_translation_block, update_tournament_text
        for key in ("tournament_help_content", "tournament_elimination_rule"):
            text = replace_translation_block(text, key, translations)
        lang_path.write_text(update_tournament_text(text))
    (directory / "game_config.json").write_text(json.dumps(config, indent=2) + "\n")


def startup_source(source, config, android=False, server_url=None):
    """Compile configured preview attributes and client-supported rules into AS3."""
    from tools.visual_assets import palette_source
    source = palette_source(str(source))
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
    return inject_server(inject_mock(source + "\n", config, android), config, android, server_url=server_url)


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
