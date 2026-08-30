from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_visible_copy_avoids_uncontracted_ranking_language() -> None:
    sources = [
        PROJECT_ROOT / "view_xy.html",
        PROJECT_ROOT / "demo" / "demo_po_meta.json",
        PROJECT_ROOT / "demo" / "demo_vo_meta.json",
    ]
    prohibited = (
        "best",
        "elite",
        "strength",
        "most academic",
        "最佳",
        "精英",
        "更强",
        "学术性最强",
        "sterker",
        "beste",
        "meest academisch",
    )

    for source in sources:
        text = source.read_text(encoding="utf-8").casefold()
        for term in prohibited:
            assert term.casefold() not in text, f"{source.name} contains ranking language: {term}"
