"""Seguridad para herramientas: validación de rutas y bloqueo de traversal."""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


class SecurityError(ValueError):
    pass


def validate_path(path: str, base_dir: Path) -> Path:
    r"""Valida que la ruta resuelta esté dentro de base_dir.

    Bloquea path traversal (../, ..\) y enlaces simbólicos que apunten
    fuera de base_dir.
    """
    base = base_dir.resolve()

    # Rechazar componentes que intenten salir
    full_path = base_dir / path
    resolved = full_path.resolve()

    # Verificar que la ruta final esté dentro de base_dir
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise SecurityError(f"Path traversal bloqueado: '{path}' está fuera de '{base_dir}'") from exc

    # Verificar cada componente por symlinks maliciosos
    current = base_dir.resolve()
    for part in Path(path).parts:
        current = current / part
        if current.is_symlink():
            target = current.resolve()
            try:
                target.relative_to(base)
            except ValueError as exc:
                raise SecurityError(
                    f"Symlink fuera de base bloqueado: '{current}' -> '{target}'"
                ) from exc

    return resolved
