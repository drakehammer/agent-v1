"""Tests unitarios para read_test."""

from pathlib import Path

from tools.read_test import read_test


def test_read_test_reads_file():
    """Debe leer un archivo y devolver su contenido."""
    samples_dir = Path(__file__).resolve().parent.parent / "data" / "samples" / "synthetic"
    samples_dir.mkdir(parents=True, exist_ok=True)
    test_file = samples_dir / "test_helper.log"
    test_file.write_text("linea1\nlinea2\nlinea3", encoding="utf-8")

    result = read_test("samples/synthetic/test_helper.log")
    assert "linea1" in result

    test_file.unlink()


def test_read_test_truncates():
    """Debe truncar a 10000 caracteres."""
    samples_dir = Path(__file__).resolve().parent.parent / "data" / "samples" / "synthetic"
    samples_dir.mkdir(parents=True, exist_ok=True)
    test_file = samples_dir / "test_large.log"
    content = "A" * 12000
    test_file.write_text(content, encoding="utf-8")

    result = read_test("samples/synthetic/test_large.log")
    assert len(result) <= 10000 + 50  # + margen para truncado

    test_file.unlink()


def test_read_test_path_traversal():
    """Debe bloquear path traversal."""
    result = read_test("../../../etc/passwd")
    assert "security" in result.lower() or "bloqueado" in result.lower()