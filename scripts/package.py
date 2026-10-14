"""Build a deterministic manual-install ZIP from integration sources only."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

root = Path(__file__).resolve().parents[1]
output = root / "dist" / "kstar_lan.zip"
output.parent.mkdir(exist_ok=True)
with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
    for path in sorted((root / "custom_components" / "kstar_lan").rglob("*")):
        if path.is_file() and path.suffix in {".py", ".json"}:
            info = ZipInfo(path.relative_to(root).as_posix(), date_time=(2026, 10, 14, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
print(output)
