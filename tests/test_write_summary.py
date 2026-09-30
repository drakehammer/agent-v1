"""Tests unitarios para write_summary."""

from pathlib import Path

from tools import security
from tools.write_summary import write_summary


def test_write_summary_creates_file(tmp_path):
    """Debe escribir un archivo .md en output/."""
    security.OUTPUT_DIR = tmp_path / "output"

    result = write_summary("summary.md", "# Hola\nTest")
    assert result["success"] is True

    output_file = tmp_path / "output" / "summary.md"
    assert output_file.exists()
    assert "# Hola" in output_file.read_text()


def test_write_summary_blocks_non_md(tmp_path):
    """Debe rechazar archivos que no sean .md."""
    security.OUTPUT_DIR = tmp_path / "output"

    result = write_summary("report.txt", "contenido")
    assert result["success"] is False
    assert ".md" in result["error"]


def test_write_summary_blocks_outside_output(tmp_path):
    """Debe bloquear escritura fuera de output/."""
    security.OUTPUT_DIR = tmp_path / "output"

    result = write_summary("../outside.md", "contenido")
    assert result["success"] is False