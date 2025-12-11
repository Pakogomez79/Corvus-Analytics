from pathlib import Path
import shutil
import pdfkit

# If wkhtmltopdf is not on PATH, set WKHTMLTOPDF_CMD to its absolute path, e.g.:
# r"C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe"
WKHTMLTOPDF_CMD = None


def _detect_wkhtmltopdf() -> str | None:
    # 1) If explicitly set, return it.
    if WKHTMLTOPDF_CMD:
        return WKHTMLTOPDF_CMD
    # 2) Try PATH
    found = shutil.which("wkhtmltopdf")
    if found:
        return found
    # 3) Common Windows install path (adjust if needed)
    default_win = Path(r"C:/Program Files/wkhtmltopdf/bin/wkhtmltopdf.exe")
    if default_win.exists():
        return str(default_win)
    return None


def get_pdfkit_config() -> pdfkit.configuration:
    cmd = _detect_wkhtmltopdf()
    if not cmd:
        raise RuntimeError(
            "wkhtmltopdf no encontrado. Instala wkhtmltopdf y configura WKHTMLTOPDF_CMD en pdf_config.py o añade el ejecutable al PATH."
        )
    return pdfkit.configuration(wkhtmltopdf=cmd)


# Optional: set default options here
PDF_OPTIONS = {
    "enable-local-file-access": None,
    "encoding": "UTF-8",
    "quiet": None,
}
