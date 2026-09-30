"""Resolución unificada de rutas de reportes."""
from pathlib import Path


def resolve_path(path_arg: str) -> Path:
    """Resuelve rutas de reporte con soporte para 'synthetic/x.xml', 'x.xml' y 'data/samples/synthetic/x.xml'."""
    p = Path(path_arg)
    if p.exists():
        return p.resolve()
    synthetic_dir = Path("data/samples/synthetic")
    if synthetic_dir.exists():
        synthetic_path = synthetic_dir / p
        if synthetic_path.exists():
            return synthetic_path.resolve()
        synthetic_path2 = synthetic_dir / p.name
        if synthetic_path2.exists():
            return synthetic_path2.resolve()
    real_dir = Path("data/samples/real")
    if real_dir.exists():
        real_path = real_dir / p
        if real_path.exists():
            return real_path.resolve()
        real_path2 = real_dir / p.name
        if real_path2.exists():
            return real_path2.resolve()
    # Intentar con prefijo data/samples/synthetic explícito
    if not path_arg.startswith("data/"):
        for base_str in ("data/samples/synthetic", "data/samples/real"):
            base = Path(base_str)
            full = base / path_arg
            if full.exists():
                return full.resolve()
            full2 = base / Path(path_arg).name
            if full2.exists():
                return full2.resolve()
    # Si llega como data/samples/synthetic/x.xml directamente
    if path_arg.startswith("data/"):
        direct = Path(path_arg)
        if direct.exists():
            return direct.resolve()
    raise FileNotFoundError(f"No se encontró el reporte: {path_arg}")
