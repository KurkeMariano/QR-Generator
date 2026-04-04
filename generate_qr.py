#!/usr/bin/env python3
"""
WiFi QR Code Generator
Generates a printable QR code image for WiFi network access.
"""

import json
import os
import re
import sys
import subprocess
import platform
import argparse
import qrcode
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

CONFIG_PATH = os.path.expanduser("~/.config/qr-generator/config.json")

# ── Persistent config ──────────────────────────────────────────────────────────

def load_config() -> dict:
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_config(data: dict) -> None:
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    current = load_config()
    current.update(data)
    with open(CONFIG_PATH, "w") as f:
        json.dump(current, f, indent=2)


# ── WiFi scanning ─────────────────────────────────────────────────────────────

def is_wsl() -> bool:
    try:
        with open("/proc/version") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


def _parse_netsh_output(text: str) -> list[str]:
    """Parse 'netsh wlan show networks mode=bssid' output (any locale)."""
    networks = []
    for line in text.splitlines():
        line = line.strip()
        # Matches "SSID             : name" or "SSID : name" (not BSSID)
        if re.match(r'^SSID\b', line, re.IGNORECASE) and "BSSID" not in line.upper():
            parts = line.split(":", 1)
            if len(parts) == 2:
                ssid = parts[1].strip()
                if ssid and ssid not in networks:
                    networks.append(ssid)
    return networks


def scan_wifi_wsl() -> list[str]:
    """Use Windows netsh.exe from within WSL."""
    for enc in ("utf-8", "cp1252", "cp850", "latin-1"):
        try:
            result = subprocess.run(
                ["netsh.exe", "wlan", "show", "networks", "mode=bssid"],
                capture_output=True, timeout=15,
            )
            text = result.stdout.decode(enc, errors="replace")
            networks = _parse_netsh_output(text)
            if networks:
                return networks
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []
    return []


def scan_wifi_linux() -> list[str]:
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "SSID", "dev", "wifi", "list"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            networks = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            if networks:
                return list(dict.fromkeys(networks))
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    try:
        result = subprocess.run(
            ["iwlist", "scanning"],
            capture_output=True, text=True, timeout=15
        )
        networks = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith('ESSID:'):
                ssid = line[7:].strip('"')
                if ssid and ssid not in networks:
                    networks.append(ssid)
        return networks
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def scan_wifi_macos() -> list[str]:
    airport = (
        "/System/Library/PrivateFrameworks/Apple80211.framework"
        "/Versions/Current/Resources/airport"
    )
    try:
        result = subprocess.run(
            [airport, "-s"],
            capture_output=True, text=True, timeout=15
        )
        networks = []
        for line in result.stdout.splitlines()[1:]:
            parts = line.split()
            if parts:
                ssid = parts[0]
                if ssid and ssid not in networks:
                    networks.append(ssid)
        return networks
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def scan_wifi_windows() -> list[str]:
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "networks", "mode=bssid"],
            capture_output=True, timeout=15,
        )
        text = result.stdout.decode("cp1252", errors="replace")
        return _parse_netsh_output(text)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def scan_networks() -> list[str]:
    system = platform.system()
    if system == "Linux":
        if is_wsl():
            return scan_wifi_wsl()
        return scan_wifi_linux()
    elif system == "Darwin":
        return scan_wifi_macos()
    elif system == "Windows":
        return scan_wifi_windows()
    return []


# ── Interactive prompts ────────────────────────────────────────────────────────

def choose_network(default: str = "") -> str:
    print("\nEscaneando redes WiFi disponibles...")
    networks = scan_networks()

    if networks:
        print("\nRedes encontradas:")
        for i, ssid in enumerate(networks, 1):
            print(f"  {i}. {ssid}")
        print(f"  {len(networks) + 1}. Ingresar manualmente")

        while True:
            try:
                choice = input("\nElegí una opción: ").strip()
                idx = int(choice)
                if 1 <= idx <= len(networks):
                    return networks[idx - 1]
                elif idx == len(networks) + 1:
                    break
                else:
                    print("Opción inválida, intentá de nuevo.")
            except ValueError:
                print("Ingresá un número.")
    else:
        print("No se pudieron detectar redes. Ingresá manualmente.")

    hint = f" [{default}]" if default else ""
    value = input(f"SSID (nombre de la red){hint}: ").strip()
    return value or default


def choose_security(label: str = "") -> str:
    suffix = f" ({label})" if label else ""
    print(f"\nTipo de seguridad{suffix}:")
    print("  1. WPA/WPA2 (más común)")
    print("  2. WEP (antiguo)")
    print("  3. Sin contraseña")
    options = {"1": "WPA", "2": "WEP", "3": "nopass"}
    while True:
        choice = input("Elegí (1/2/3) [1]: ").strip() or "1"
        if choice in options:
            return options[choice]
        print("Opción inválida.")


# ── QR generation ─────────────────────────────────────────────────────────────

def build_wifi_string(ssid: str, password: str, security: str, hidden: bool = False) -> str:
    def escape(value: str) -> str:
        for ch in ('\\', ';', ',', '"', ':'):
            value = value.replace(ch, '\\' + ch)
        return value

    h = "true" if hidden else "false"
    if security == "nopass":
        return f"WIFI:T:nopass;S:{escape(ssid)};H:{h};;"
    return f"WIFI:T:{security};S:{escape(ssid)};P:{escape(password)};H:{h};;"


def _find_font_path() -> str | None:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _make_qr_obj(data: str, error_correction=qrcode.constants.ERROR_CORRECT_M) -> qrcode.QRCode:
    qr = qrcode.QRCode(
        version=None,
        error_correction=error_correction,
        box_size=20,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr


def _overlay_logo(qr_img: Image.Image, logo_path: str) -> Image.Image:
    """Overlay a logo in the center of the QR code (max ~25% of QR size)."""
    try:
        logo = Image.open(logo_path).convert("RGBA")
    except (FileNotFoundError, OSError) as e:
        print(f"Advertencia: no se pudo abrir el logo ({e}). Continuando sin logo.",
              file=sys.stderr)
        return qr_img

    qr_w, qr_h = qr_img.size
    max_logo = min(qr_w, qr_h) // 4

    logo_w, logo_h = logo.size
    ratio = min(max_logo / logo_w, max_logo / logo_h)
    new_size = (int(logo_w * ratio), int(logo_h * ratio))
    logo = logo.resize(new_size, Image.LANCZOS)

    pad = 8
    padded = Image.new("RGBA", (new_size[0] + pad * 2, new_size[1] + pad * 2), (255, 255, 255, 255))
    mask = logo if logo.mode == "RGBA" else None
    padded.paste(logo, (pad, pad), mask)

    px = (qr_w - padded.width) // 2
    py = (qr_h - padded.height) // 2

    qr_rgba = qr_img.convert("RGBA")
    qr_rgba.paste(padded, (px, py), padded)
    return qr_rgba.convert("RGB")


def print_ascii_preview(data: str) -> None:
    qr = _make_qr_obj(data)
    print("\n── Vista previa ──────────────────────────────")
    qr.print_ascii(invert=True)
    print("──────────────────────────────────────────────\n")


# Credit card dimensions: ISO/IEC 7810 ID-1, landscape
_CARD_W_MM, _CARD_H_MM = 85.6, 54.0
_CARD_DPI = 300
_CARD_W = round(_CARD_W_MM * _CARD_DPI / 25.4)  # 1010 px
_CARD_H = round(_CARD_H_MM * _CARD_DPI / 25.4)  # 638 px


def _build_card_canvas(
    data: str,
    label: str,
    fg_color: str = "black",
    bg_color: str = "white",
    logo_path: str | None = None,
) -> Image.Image:
    """Render a single credit-card-sized canvas (1010 × 638 px)."""
    MARGIN = 24

    error_correction = (
        qrcode.constants.ERROR_CORRECT_H if logo_path
        else qrcode.constants.ERROR_CORRECT_M
    )
    qr = _make_qr_obj(data, error_correction)

    qr_size = _CARD_H - 2 * MARGIN
    qr_img = qr.make_image(fill_color=fg_color, back_color=bg_color).convert("RGB")
    qr_img = qr_img.resize((qr_size, qr_size), Image.NEAREST)

    if logo_path:
        qr_img = _overlay_logo(qr_img, logo_path)

    canvas = Image.new("RGB", (_CARD_W, _CARD_H), bg_color)
    canvas.paste(qr_img, (MARGIN, MARGIN))

    draw = ImageDraw.Draw(canvas)

    border_color = "#BBBBBB" if bg_color.lower() in ("white", "#ffffff", "#fff") else fg_color
    draw.rectangle([(1, 1), (_CARD_W - 2, _CARD_H - 2)], outline=border_color, width=3)

    text_x = MARGIN + qr_size + MARGIN
    text_w = _CARD_W - text_x - MARGIN
    font_path = _find_font_path()

    def fit_text(text: str, max_w: int, max_size: int, min_size: int = 22):
        if not font_path:
            return ImageFont.load_default()
        for size in range(max_size, min_size - 1, -2):
            try:
                f = ImageFont.truetype(font_path, size)
            except OSError:
                return ImageFont.load_default()
            bbox = draw.textbbox((0, 0), text, font=f)
            if bbox[2] - bbox[0] <= max_w:
                return f
        return ImageFont.load_default()

    f_title = fit_text("WiFi", text_w, 54)
    f_label = fit_text(label, text_w - 8, 38)
    f_sub   = fit_text("Escaneá para", text_w, 28)

    def centered(y: int, text: str, font, color: str = fg_color) -> None:
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        x = text_x + max(0, (text_w - w) // 2)
        draw.text((x, y), text, fill=color, font=font)

    h_title = draw.textbbox((0, 0), "WiFi", font=f_title)[3]
    h_label = draw.textbbox((0, 0), label,  font=f_label)[3]
    h_sub   = draw.textbbox((0, 0), "A",    font=f_sub)[3]
    GAP1, SEP, GAP2, GAP3 = 12, 2, 18, 24
    block_h = h_title + GAP1 + SEP + GAP2 + h_label + GAP3 + h_sub + 6 + h_sub + 6

    y = MARGIN + (_CARD_H - 2 * MARGIN - block_h) // 2

    sub_color = "#777777" if bg_color.lower() in ("white", "#ffffff", "#fff") else fg_color
    sep_color = "#CCCCCC" if bg_color.lower() in ("white", "#ffffff", "#fff") else fg_color

    centered(y, "WiFi", f_title)
    y += h_title + GAP1

    draw.line([(text_x, y), (text_x + text_w, y)], fill=sep_color, width=SEP)
    y += SEP + GAP2

    centered(y, label, f_label)
    y += h_label + GAP3

    centered(y, "Escaneá para", f_sub, sub_color)
    y += h_sub + 6
    centered(y, "conectarte", f_sub, sub_color)

    return canvas


def _save_image(img: Image.Image, path: str) -> None:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        img.save(path, "PDF", resolution=_CARD_DPI)
    else:
        img.save(path, "PNG", dpi=(_CARD_DPI, _CARD_DPI))


def generate_qr_card(
    data: str,
    label: str,
    output_path: str,
    fg_color: str = "black",
    bg_color: str = "white",
    logo_path: str | None = None,
) -> str:
    canvas = _build_card_canvas(data, label, fg_color, bg_color, logo_path)
    _save_image(canvas, output_path)
    return output_path


def generate_qr_dual(
    data1: str, label1: str,
    data2: str, label2: str,
    output_path: str,
    fg_color: str = "black",
    bg_color: str = "white",
    logo_path: str | None = None,
) -> str:
    """Two credit-card layouts stacked vertically (85.6 × ~110 mm)."""
    card1 = _build_card_canvas(data1, label1, fg_color, bg_color, logo_path)
    card2 = _build_card_canvas(data2, label2, fg_color, bg_color, logo_path)

    GAP = 24  # ~2 mm gap between the two cards
    combined = Image.new("RGB", (_CARD_W, _CARD_H * 2 + GAP), bg_color)
    combined.paste(card1, (0, 0))
    combined.paste(card2, (0, _CARD_H + GAP))

    _save_image(combined, output_path)
    return output_path


def generate_qr_svg(data: str, output_path: str) -> str:
    """Generate a plain scalable SVG QR code."""
    import qrcode.image.svg as svg_mod
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(image_factory=svg_mod.SvgImage)
    img.save(output_path)
    return output_path


def generate_qr_image(
    data: str,
    label: str,
    output_path: str,
    include_label: bool = True,
    fg_color: str = "black",
    bg_color: str = "white",
    logo_path: str | None = None,
) -> str:
    """Simple large QR with optional label (non-card layout)."""
    error_correction = (
        qrcode.constants.ERROR_CORRECT_H if logo_path
        else qrcode.constants.ERROR_CORRECT_M
    )
    qr = _make_qr_obj(data, error_correction)
    qr_img = qr.make_image(fill_color=fg_color, back_color=bg_color).convert("RGB")

    if logo_path:
        qr_img = _overlay_logo(qr_img, logo_path)

    if not include_label:
        qr_img.save(output_path, "PNG", dpi=(_CARD_DPI, _CARD_DPI))
        return output_path

    qr_w, qr_h = qr_img.size
    label_height = 120
    canvas = Image.new("RGB", (qr_w, qr_h + label_height), bg_color)
    canvas.paste(qr_img, (0, 0))

    draw = ImageDraw.Draw(canvas)
    font_path = _find_font_path()
    f_large = f_small = None
    if font_path:
        try:
            f_large = ImageFont.truetype(font_path, 48)
            f_small = ImageFont.truetype(font_path, 30)
        except OSError:
            pass
    if f_large is None:
        f_large = f_small = ImageFont.load_default()

    text = f"Red WiFi: {label}"
    bbox = draw.textbbox((0, 0), text, font=f_large)
    x = (qr_w - (bbox[2] - bbox[0])) // 2
    draw.text((x, qr_h + 10), text, fill=fg_color, font=f_large)

    sub = "Escaneá para conectarte"
    bbox2 = draw.textbbox((0, 0), sub, font=f_small)
    x2 = (qr_w - (bbox2[2] - bbox2[0])) // 2
    sub_color = "#555555" if bg_color.lower() in ("white", "#ffffff", "#fff") else fg_color
    draw.text((x2, qr_h + 68), sub, fill=sub_color, font=f_small)

    canvas.save(output_path, "PNG", dpi=(_CARD_DPI, _CARD_DPI))
    return output_path


# ── CLI entry point ────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Genera un QR listo para imprimir (WiFi, URL o texto).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # QR WiFi en tarjeta de crédito (PDF)
  python generate_qr.py --pdf

  # Con logo y colores personalizados
  python generate_qr.py --ssid MiRed --pdf --logo logo.png --fg-color "#003366"

  # Red principal + red de invitados en una sola imagen
  python generate_qr.py --ssid MiRed --ssid2 MiRed_Guest --pdf

  # Ver QR en la terminal antes de guardar
  python generate_qr.py --preview

  # QR de URL
  python generate_qr.py --type url --data "https://ejemplo.com" --svg

  # QR de texto libre
  python generate_qr.py --type text --data "Contraseña: abc123"
        """,
    )

    # ── Tipo de QR ──
    parser.add_argument(
        "--type", dest="qr_type", choices=["wifi", "url", "text"],
        default="wifi", metavar="TIPO",
        help="Tipo de QR: wifi (default), url, text",
    )
    parser.add_argument("--data", help="Datos para --type url o --type text")

    # ── Red principal ──
    parser.add_argument("--ssid", help="Nombre de la red WiFi")
    parser.add_argument("--password", help="Contraseña de la red")
    parser.add_argument(
        "--security", choices=["WPA", "WEP", "nopass"], default=None,
        help="Tipo de seguridad (default: WPA)",
    )
    parser.add_argument("--hidden", action="store_true", help="Red oculta")

    # ── Segunda red (modo dual) ──
    parser.add_argument("--ssid2", help="Segunda red WiFi (genera imagen con ambas redes)")
    parser.add_argument("--password2", help="Contraseña de la segunda red")
    parser.add_argument("--security2", choices=["WPA", "WEP", "nopass"], default=None)

    # ── Visual ──
    parser.add_argument("--logo", help="Ruta a imagen de logo para centrar en el QR")
    parser.add_argument("--fg-color", default="black", metavar="COLOR",
                        help='Color del QR, e.g. "#003366" (default: black)')
    parser.add_argument("--bg-color", default="white", metavar="COLOR",
                        help='Color de fondo, e.g. "#f0f0f0" (default: white)')

    # ── Salida ──
    parser.add_argument("--output", default=None, help="Ruta del archivo de salida")
    parser.add_argument("--no-label", action="store_true",
                        help="No agregar etiqueta (solo para PNG sin tarjeta)")
    parser.add_argument(
        "--pdf", action="store_true",
        help="Generar PDF tamaño tarjeta de crédito (85.6 × 54 mm, landscape)",
    )
    parser.add_argument("--svg", action="store_true",
                        help="Generar SVG vectorial (solo QR, sin layout de tarjeta)")
    parser.add_argument("--preview", action="store_true",
                        help="Mostrar QR en la terminal antes de guardar")

    return parser.parse_args()


def main():
    args = parse_args()
    cfg = load_config()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ── Modo URL / Texto ────────────────────────────────────────────────────────
    if args.qr_type in ("url", "text"):
        data = args.data or input("Ingresá el dato: ").strip()
        if not data:
            print("Error: no se ingresó ningún dato.", file=sys.stderr)
            sys.exit(1)

        if args.preview:
            print_ascii_preview(data)

        short = data[:40].replace("/", "_").replace(":", "")
        if args.svg:
            output = args.output or f"qr_{args.qr_type}_{timestamp}.svg"
            generate_qr_svg(data, output)
        elif args.pdf:
            output = args.output or f"qr_{args.qr_type}_{timestamp}.pdf"
            generate_qr_card(data, short, output, args.fg_color, args.bg_color, args.logo)
        else:
            output = args.output or f"qr_{args.qr_type}_{timestamp}.png"
            generate_qr_image(data, short, output, not args.no_label,
                              args.fg_color, args.bg_color, args.logo)

        print(f"\nQR generado: {output}")
        return

    # ── Modo WiFi ───────────────────────────────────────────────────────────────

    # SSID con hint del último uso
    if args.ssid:
        ssid = args.ssid
    else:
        ssid = choose_network(default=cfg.get("ssid", ""))

    if not ssid:
        print("Error: no se ingresó ningún SSID.", file=sys.stderr)
        sys.exit(1)

    # Seguridad con hint del último uso
    if args.security:
        security = args.security
    else:
        last_sec = cfg.get("security", "WPA")
        print(f"\nTipo de seguridad (último: {last_sec}):")
        print("  1. WPA/WPA2 (más común)")
        print("  2. WEP (antiguo)")
        print("  3. Sin contraseña")
        options = {"1": "WPA", "2": "WEP", "3": "nopass"}
        rev = {"WPA": "1", "WEP": "2", "nopass": "3"}
        default_num = rev.get(last_sec, "1")
        while True:
            choice = input(f"Elegí (1/2/3) [{default_num}]: ").strip() or default_num
            if choice in options:
                security = options[choice]
                break
            print("Opción inválida.")

    # Contraseña
    if security == "nopass":
        password = ""
    elif args.password is not None:
        password = args.password
    else:
        import getpass
        password = getpass.getpass(f"Contraseña para '{ssid}': ")

    safe_ssid = "".join(c if c.isalnum() or c in "-_" else "_" for c in ssid)
    wifi_str1 = build_wifi_string(ssid, password, security, args.hidden)

    if args.preview:
        print_ascii_preview(wifi_str1)

    # Guardar configuración para el próximo uso
    save_config({"ssid": ssid, "security": security})

    # ── Modo dual (dos redes) ───────────────────────────────────────────────────
    if args.ssid2:
        ssid2 = args.ssid2
        security2 = args.security2 or choose_security("segunda red")
        if security2 == "nopass":
            password2 = ""
        elif args.password2 is not None:
            password2 = args.password2
        else:
            import getpass
            password2 = getpass.getpass(f"Contraseña para '{ssid2}': ")

        wifi_str2 = build_wifi_string(ssid2, password2, security2, args.hidden)
        ext = ".pdf" if args.pdf else ".png"
        output = args.output or f"wifi_qr_dual_{safe_ssid}_{timestamp}{ext}"
        generate_qr_dual(
            wifi_str1, ssid, wifi_str2, ssid2,
            output, args.fg_color, args.bg_color, args.logo,
        )
        print(f"\nQR dual generado: {output}")
        print(f"  Red 1: {ssid}")
        print(f"  Red 2: {ssid2}")
        if args.pdf:
            print("Formato: PDF con dos tarjetas apiladas — recortá cada una")
        return

    # ── Salida simple ───────────────────────────────────────────────────────────
    if args.svg:
        output = args.output or f"wifi_qr_{safe_ssid}_{timestamp}.svg"
        generate_qr_svg(wifi_str1, output)
        print(f"\nQR SVG generado: {output}")
    elif args.pdf:
        output = args.output or f"wifi_qr_{safe_ssid}_{timestamp}.pdf"
        generate_qr_card(wifi_str1, ssid, output, args.fg_color, args.bg_color, args.logo)
        print(f"\nQR generado: {output}")
        print("Formato: PDF tarjeta de crédito (85.6 × 54 mm) — listo para imprimir y recortar")
    else:
        output = args.output or f"wifi_qr_{safe_ssid}_{timestamp}.png"
        generate_qr_image(wifi_str1, ssid, output, not args.no_label,
                          args.fg_color, args.bg_color, args.logo)
        print(f"\nQR generado: {output}")
        print("Resolución: 300 DPI — listo para imprimir")


if __name__ == "__main__":
    main()
