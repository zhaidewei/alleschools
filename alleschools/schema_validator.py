import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION_SUPPORTED = "1.0.0"


@dataclass
class ValidationError:
    kind: str
    message: str
    path: str

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": self.kind, "message": self.message, "path": self.path}


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"ERROR: file not found: {path}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"ERROR: invalid JSON in {path}: {e}")


def validate_points_schema(data: Any, layer: str) -> List[ValidationError]:
    errors: List[ValidationError] = []

    if not isinstance(data, list):
        errors.append(
            ValidationError(
                kind="type_error",
                message="points data must be a JSON array",
                path="$",
            )
        )
        return errors

    required_fields = [
        "id",
        "layer",
        "brin",
        "name",
        "municipality",
        "postcode",
        "pc4",
        "school_type",
        "x_linear",
        "y_linear",
        "size",
        "years_covered",
        "flags",
    ]

    for idx, obj in enumerate(data):
        base_path = f"$[{idx}]"
        if not isinstance(obj, dict):
            errors.append(
                ValidationError(
                    kind="type_error",
                    message="each point must be a JSON object",
                    path=base_path,
                )
            )
            continue

        for field in required_fields:
            if field not in obj:
                errors.append(
                    ValidationError(
                        kind="missing_field",
                        message=f"missing required field '{field}'",
                        path=f"{base_path}.{field}",
                    )
                )

        if "layer" in obj and obj.get("layer") != layer:
            errors.append(
                ValidationError(
                    kind="value_error",
                    message=f"layer must be '{layer}'",
                    path=f"{base_path}.layer",
                )
            )

        # Basic type checks
        for num_field in ("x_linear", "y_linear", "size"):
            if num_field in obj and not isinstance(obj[num_field], (int, float)):
                errors.append(
                    ValidationError(
                        kind="type_error",
                        message=f"field '{num_field}' must be number",
                        path=f"{base_path}.{num_field}",
                    )
                )

        if "years_covered" in obj and not isinstance(obj["years_covered"], list):
            errors.append(
                ValidationError(
                    kind="type_error",
                    message="years_covered must be an array of strings",
                    path=f"{base_path}.years_covered",
                )
            )

        if "flags" in obj and not isinstance(obj["flags"], dict):
            errors.append(
                ValidationError(
                    kind="type_error",
                    message="flags must be an object",
                    path=f"{base_path}.flags",
                )
            )

    return errors


def validate_geojson_schema(data: Any, layer: str) -> List[ValidationError]:
    """
    Validate basic GeoJSON structure for generated *_geo.json files.

    We intentionally keep this light-weight and focused on the contract that
    alleschools.exporters.geojson_exporter guarantees:
    - a top-level FeatureCollection
    - each feature has properties carrying the original wide-table columns
      (at least BRIN / X_linear / Y_linear)
    - geometry is either null or a Point with [lon, lat] numeric coordinates
    """
    errors: List[ValidationError] = []

    if not isinstance(data, dict):
        errors.append(
            ValidationError(
                kind="type_error",
                message="GeoJSON root must be an object",
                path="$",
            )
        )
        return errors

    if data.get("type") != "FeatureCollection":
        errors.append(
            ValidationError(
                kind="value_error",
                message="GeoJSON.type must be 'FeatureCollection'",
                path="$.type",
            )
        )

    features = data.get("features")
    if not isinstance(features, list):
        errors.append(
            ValidationError(
                kind="type_error",
                message="GeoJSON.features must be an array",
                path="$.features",
            )
        )
        return errors

    for idx, feat in enumerate(features):
        base_path = f"$.features[{idx}]"
        if not isinstance(feat, dict):
            errors.append(
                ValidationError(
                    kind="type_error",
                    message="each feature must be an object",
                    path=base_path,
                )
            )
            continue

        if feat.get("type") != "Feature":
            errors.append(
                ValidationError(
                    kind="value_error",
                    message="feature.type must be 'Feature'",
                    path=f"{base_path}.type",
                )
            )

        props = feat.get("properties")
        if not isinstance(props, dict):
            errors.append(
                ValidationError(
                    kind="type_error",
                    message="feature.properties must be an object",
                    path=f"{base_path}.properties",
                )
            )
        else:
            # BRIN is the primary key carried from the wide table
            for required_prop in ("BRIN", "X_linear", "Y_linear"):
                if required_prop not in props:
                    errors.append(
                        ValidationError(
                            kind="missing_field",
                            message=f"missing required property '{required_prop}'",
                            path=f"{base_path}.properties.{required_prop}",
                        )
                    )

        geom = feat.get("geometry")
        if geom is None:
            continue
        if not isinstance(geom, dict):
            errors.append(
                ValidationError(
                    kind="type_error",
                    message="geometry must be an object or null",
                    path=f"{base_path}.geometry",
                )
            )
            continue
        if geom.get("type") != "Point":
            errors.append(
                ValidationError(
                    kind="value_error",
                    message="geometry.type must be 'Point' when present",
                    path=f"{base_path}.geometry.type",
                )
            )
        coords = geom.get("coordinates")
        if not (isinstance(coords, list) and len(coords) == 2):
            errors.append(
                ValidationError(
                    kind="type_error",
                    message="geometry.coordinates must be [lon, lat]",
                    path=f"{base_path}.geometry.coordinates",
                )
            )
        else:
            lon, lat = coords
            if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
                errors.append(
                    ValidationError(
                        kind="type_error",
                        message="geometry.coordinates must contain numeric [lon, lat]",
                        path=f"{base_path}.geometry.coordinates",
                    )
                )

    return errors


def validate_long_table_schema(rows: Any, layer: str) -> List[ValidationError]:
    """
    Validate the long-table CSV structure after expansion by long_table_exporter.

    This works on already-parsed rows (e.g. list(csv.DictReader(...))).
    We assert:
      - rows is a sequence of dict-like objects
      - required columns are present (BRIN, year, X_linear, Y_linear and size column)
      - numeric columns have parseable numeric values when non-empty
    """
    errors: List[ValidationError] = []

    if not isinstance(rows, list):
        errors.append(
            ValidationError(
                kind="type_error",
                message="long-table rows must be a list",
                path="$",
            )
        )
        return errors

    if not rows:
        # empty is allowed but not very useful; no further checks
        return errors

    first = rows[0]
    if not isinstance(first, dict):
        errors.append(
            ValidationError(
                kind="type_error",
                message="each long-table row must be an object",
                path="$[0]",
            )
        )
        return errors

    header_keys = set(first.keys())
    size_field = "pupils_total" if layer == "po" else "candidates_total"
    required_cols = {"BRIN", "year", "X_linear", "Y_linear", size_field}

    missing = sorted(required_cols - header_keys)
    for col in missing:
        errors.append(
            ValidationError(
                kind="missing_field",
                message=f"missing required column '{col}' in long-table header",
                path=f"$.header.{col}",
            )
        )

    # Per-row numeric checks
    def _check_numeric(val: Any, path: str) -> None:
        if val in ("", None):
            return
        try:
            float(val)
        except (TypeError, ValueError):
            errors.append(
                ValidationError(
                    kind="type_error",
                    message="value must be numeric-compatible",
                    path=path,
                )
            )

    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(
                ValidationError(
                    kind="type_error",
                    message="each long-table row must be an object",
                    path=f"$[{idx}]",
                )
            )
            continue
        for col in ("X_linear", "Y_linear", size_field):
            if col in row:
                _check_numeric(row.get(col), path=f"$[{idx}].{col}")

    return errors


def validate_meta_schema(meta: Any, expected_layer: str) -> List[ValidationError]:
    errors: List[ValidationError] = []
    path_root = "$"

    if not isinstance(meta, dict):
        errors.append(
            ValidationError(
                kind="type_error",
                message="meta must be a JSON object",
                path=path_root,
            )
        )
        return errors

    # Top-level required fields
    for field in ("version", "layer", "axes", "fields", "i18n"):
        if field not in meta:
            errors.append(
                ValidationError(
                    kind="missing_field",
                    message=f"missing required field '{field}'",
                    path=f"{path_root}.{field}",
                )
            )

    version = meta.get("version")
    if isinstance(version, str) and version != SCHEMA_VERSION_SUPPORTED:
        errors.append(
            ValidationError(
                kind="version_mismatch",
                message=f"meta version '{version}' is not supported "
                f"(expected {SCHEMA_VERSION_SUPPORTED})",
                path="$.version",
            )
        )

    if meta.get("layer") != expected_layer:
        errors.append(
            ValidationError(
                kind="value_error",
                message=f"meta.layer must be '{expected_layer}'",
                path="$.layer",
            )
        )

    axes = meta.get("axes", {})
    if not isinstance(axes, dict):
        errors.append(
            ValidationError(
                kind="type_error",
                message="axes must be an object",
                path="$.axes",
            )
        )
    else:
        for key in ("x", "y", "size"):
            if key not in axes:
                errors.append(
                    ValidationError(
                        kind="missing_field",
                        message=f"axes must define '{key}'",
                        path=f"$.axes.{key}",
                    )
                )

    fields = meta.get("fields", {})
    if not isinstance(fields, dict):
        errors.append(
            ValidationError(
                kind="type_error",
                message="fields must be an object",
                path="$.fields",
            )
        )

    i18n = meta.get("i18n", {})
    if not isinstance(i18n, dict):
        errors.append(
            ValidationError(
                kind="type_error",
                message="i18n must be an object",
                path="$.i18n",
            )
        )

    # Cross-check axes.field with fields and metrics with i18n
    if isinstance(axes, dict) and isinstance(fields, dict) and isinstance(i18n, dict):
        metric_ids: List[str] = []
        field_names: List[str] = list(fields.keys())

        for k in ("x", "y", "size"):
            axis = axes.get(k)
            axis_path = f"$.axes.{k}"
            if not isinstance(axis, dict):
                continue

            field_name = axis.get("field")
            if field_name and field_name not in field_names:
                errors.append(
                    ValidationError(
                        kind="unknown_field",
                        message=f"axis '{k}' references unknown field '{field_name}'",
                        path=f"{axis_path}.field",
                    )
                )

            metric_id = axis.get("metric_id")
            if metric_id:
                metric_ids.append(metric_id)

        # Validate that metric_ids exist in each language block if present
        for lang, lang_block in i18n.items():
            if not isinstance(lang_block, dict):
                errors.append(
                    ValidationError(
                        kind="type_error",
                        message=f"i18n.{lang} must be an object",
                        path=f"$.i18n.{lang}",
                    )
                )
                continue

            metrics = lang_block.get("metrics", {})
            if not isinstance(metrics, dict):
                errors.append(
                    ValidationError(
                        kind="type_error",
                        message=f"i18n.{lang}.metrics must be an object",
                        path=f"$.i18n.{lang}.metrics",
                    )
                )
                continue

            for metric_id in metric_ids:
                if metric_id not in metrics:
                    errors.append(
                        ValidationError(
                            kind="missing_metric_i18n",
                            message=f"missing i18n for metric_id '{metric_id}' in language '{lang}'",
                            path=f"$.i18n.{lang}.metrics",
                        )
                    )

    return errors


def validate_points_against_meta(
    points: Any, meta: Any, layer: str
) -> List[ValidationError]:
    """
    High-level validation that also checks consistency between
    data fields and meta.axes / meta.fields.
    """
    errors: List[ValidationError] = []
    errors.extend(validate_points_schema(points, layer))
    errors.extend(validate_meta_schema(meta, layer))
    return errors


def _print_errors(errors: Iterable[ValidationError]) -> None:
    for err in errors:
        obj = err.to_dict()
        sys.stderr.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate AlleSchools points data + meta JSON files "
            "against refactor/SCHEMA.md (version 1.0.0)."
        )
    )
    parser.add_argument(
        "--schema-version",
        default=SCHEMA_VERSION_SUPPORTED,
        help=f"schema version to validate against (default: {SCHEMA_VERSION_SUPPORTED})",
    )
    parser.add_argument(
        "--layer",
        choices=["vo", "po"],
        required=True,
        help="data layer to validate (vo or po)",
    )
    parser.add_argument(
        "--data",
        required=True,
        help="path to points data JSON file (array of schools)",
    )
    parser.add_argument(
        "--meta",
        required=True,
        help="path to meta JSON file describing axes/fields/i18n",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.schema_version != SCHEMA_VERSION_SUPPORTED:
        sys.stderr.write(
            f"WARNING: requested schema version {args.schema_version} "
            f"but only {SCHEMA_VERSION_SUPPORTED} is supported; continuing.\n"
        )

    data_path = Path(args.data)
    meta_path = Path(args.meta)

    points = _load_json(data_path)
    meta = _load_json(meta_path)

    errors = validate_points_against_meta(points, meta, args.layer)

    if errors:
        _print_errors(errors)
        sys.stderr.write(
            f"Schema validation FAILED for layer={args.layer} "
            f"data={data_path} meta={meta_path} "
            f"({len(errors)} error(s)).\n"
        )
        return 1

    print(
        json.dumps(
            {
                "status": "ok",
                "layer": args.layer,
                "schema_version": SCHEMA_VERSION_SUPPORTED,
                "data": str(data_path),
                "meta": str(meta_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

