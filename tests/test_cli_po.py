"""测试 alleschools.cli 的 PO / VO 子命令。"""

from alleschools import cli


class DummyArgs:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_build_parser_parses_po_command():
    parser = cli.build_parser()
    args = parser.parse_args(["po"])
    assert args.command == "po"


def test_build_parser_parses_vo_command():
    parser = cli.build_parser()
    args = parser.parse_args(["vo"])
    assert args.command == "vo"


def test_make_effective_config_uses_overrides(tmp_path, monkeypatch):
    parser = cli.build_parser()
    args = parser.parse_args(
        ["--data-root", str(tmp_path), "--output-root", str(tmp_path), "po"]
    )

    cfg = cli.make_effective_config(args)
    assert cfg["data_root"] == str(tmp_path)
    assert cfg["output_root"] == str(tmp_path)

