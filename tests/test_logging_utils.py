"""测试 logging_utils 的基础行为。"""

from pathlib import Path

from alleschools.logging_utils import setup_logger


def test_setup_logger_writes_json_log(tmp_path: Path):
    log_path = tmp_path / "run.log.jsonl"
    logger = setup_logger(name="alleschools_test", json_log_path=log_path)

    logger.info("hello world")

    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8").strip()
    assert content.startswith('{"ts":')
    assert '"hello world"' in content

