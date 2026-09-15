"""Shared coarse ontology for sex-comparable fly connectome graphs."""

GROUPS = [
    "visual_sensory", "olfactory", "gustatory", "mechanosensory",
    "thermo_hygro", "other_sensory", "visual_processing",
    "learning_memory", "central_complex", "central_other", "descending",
    "ascending", "vnc_intrinsic", "motor_efferent",
    "modulatory_endocrine", "unknown",
]


def male_group(row: dict) -> int:
    sup = (row.get("superclass") or "").lower()
    cls = (row.get("class") or "").lower()
    sub = (row.get("subclass") or "").lower()
    if cls == "visual" or sup == "ol_sensory":
        return 0
    if cls == "olfactory":
        return 1
    if cls in {"gustatory", "chemosensory"}:
        return 2
    if "mechanosensory" in cls or sub in {"auditory", "wind_gravity", "chordotonal organ", "hair plate"}:
        return 3
    if cls in {"thermosensory", "hygrosensory"}:
        return 4
    if "sensory" in sup or cls == "unknown_sensory":
        return 5
    if sup in {"ol_intrinsic", "visual_projection", "visual_centrifugal", "visual_projection_tbc"}:
        return 6
    if cls in {"kenyon_cell", "mbon", "dan"}:
        return 7
    if cls == "cx":
        return 8
    if "descending" in sup:
        return 10
    if "ascending" in sup:
        return 11
    if sup == "vnc_intrinsic" or sup == "vnc_tbc":
        return 12
    if "motor" in sup or "efferent" in sup:
        return 13
    if "endocrine" in sup or (row.get("fruDsx") or ""):
        return 14
    if sup in {"cb_intrinsic", "ens"} or cls:
        return 9
    return 15


def female_group(name: str, region: str) -> int:
    if name.startswith("VIS_R"):
        return 0
    if name.startswith("VIS_"):
        return 6
    if name.startswith("OLF_"):
        return 1
    if name.startswith("GUS_"):
        return 2
    if name.startswith(("MECH_", "ANTENNAL_")):
        return 3
    if name.startswith("THERMO_"):
        return 4
    if name == "NOCI" or name == "GENERIC_SENSORY":
        return 5
    if name.startswith("MB_"):
        return 7
    if name.startswith("CX_"):
        return 8
    if name == "GNG_DESC" or name.startswith("DN_"):
        return 10
    if name.startswith("VNC_"):
        return 12
    if name.startswith("MN_") or name == "GENERIC_MOTOR":
        return 13
    if name.startswith(("DRIVE_", "CLOCK_")):
        return 14
    if region == "central":
        return 9
    return 15


def normalize(matrix: list[list[float]]) -> list[list[float]]:
    for row in matrix:
        scale = sum(abs(x) for x in row)
        if scale:
            for j, value in enumerate(row):
                row[j] = round(value / scale, 8)
    return matrix

