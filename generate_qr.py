#!/usr/bin/env python3
"""
WiFi QR Code Generator
Generates a printable QR code image for WiFi network access.
"""

import os
import sys
import subprocess
import platform
import argparse
import qrcode
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime


# ── WiFi scanning ─────────────────────────────────────────────────────────────

def scan_wifi_linux() -> list[str]:
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "SSID", "dev", "wifi", "list"],
            capture_output=True, text=True, timeout=10
        )
        networks = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return list(dict.fromkeys(networks))  # deduplicate preserving order
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
        for line in result.stdout.splitlines()[1:]:  # skip header
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
            capture_output=True, text=True, timeout=15
        )
        networks = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("SSID") and "BSSID" not in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    ssid = parts[1].strip()
                    if ssid and ssid not in networks:
                        networks.append(ssid)
        return networks
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def scan_networks() -> list[str]:
    system = platform.system()
    if system == "Linux":
        return scan_wifi_linux()
    elif system == "Darwin":
        return scan_wifi_macos()
    elif system == "Windows":
        return scan_wifi_windows()
    return []


# ── Interactive prompts ────────────────────────────────────────────────────────

def choose_network() -> str:
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

    return input("SSID (nombre de la red): ").strip()


def choose_security() -> str:
    print("\nTipo de seguridad:")
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
    """Format: WIFI:T:<security>;S:<ssid>;P:<password>;H:<hidden>;;"""
    def escape(value: str) -> str:
        # Escape special characters per WiFi QR spec
        for ch in ('\\', ';', ',', '"', ':'):
            value = value.replace(ch, '\\' + ch)
        return value

    h = "true" if hidden else "false"
    if security == "nopass":
        return f"WIFI:T:nopass;S:{escape(ssid)};H:{h};;"
    return f"WIFI:T:{security};S:{escape(ssid)};P:{escape(password)};H:{h};;"


def generate_qr_image(
    wifi_string: str,
    ssid: str,
    output_path: str,
    include_label: bool = True,
) -> str:
    qr = qrcode.QRCode(
        version=None,          # auto-size
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=20,           # large boxes → high res for printing
        border=4,
    )
    qr.add_data(wifi_string)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    if not include_label:
        qr_img.save(output_path, "PNG", dpi=(300, 300))
        return output_path

    # Add label below the QR
    qr_w, qr_h = qr_img.size
    label_height = 120
    canvas = Image.new("RGB", (qr_w, qr_h + label_height), "white")
    canvas.paste(qr_img, (0, 0))

    draw = ImageDraw.Draw(canvas)

    # Try to load a decent font, fall back to default
    font_large = None
    font_small = None
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in font_candidates:
        if os.path.exists(path):
            try:
                font_large = ImageFont.truetype(path, 48)
                font_small = ImageFont.truetype(path, 30)
                break
            except OSError:
                pass

    if font_large is None:
        font_large = ImageFont.load_default()
        font_small = font_large

    # Network name centered
    text = f"Red WiFi: {ssid}"
    bbox = draw.textbbox((0, 0), text, font=font_large)
    text_w = bbox[2] - bbox[0]
    x = (qr_w - text_w) // 2
    draw.text((x, qr_h + 10), text, fill="black", font=font_large)

    # Sub-label
    sub = "Escaneá para conectarte"
    bbox2 = draw.textbbox((0, 0), sub, font=font_small)
    sub_w = bbox2[2] - bbox2[0]
    x2 = (qr_w - sub_w) // 2
    draw.text((x2, qr_h + 68), sub, fill="#555555", font=font_small)

    canvas.save(output_path, "PNG", dpi=(300, 300))
    return output_path


# ── CLI entry point ────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Genera un QR de WiFi listo para imprimir."
    )
    parser.add_argument("--ssid", help="Nombre de la red WiFi")
    parser.add_argument("--password", help="Contraseña de la red")
    parser.add_argument(
        "--security", choices=["WPA", "WEP", "nopass"], default=None,
        help="Tipo de seguridad (default: WPA)"
    )
    parser.add_argument("--hidden", action="store_true", help="Red oculta")
    parser.add_argument("--output", default=None, help="Ruta de salida del PNG")
    parser.add_argument(
        "--no-label", action="store_true", help="No agregar etiqueta con el nombre"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # SSID
    if args.ssid:
        ssid = args.ssid
    else:
        ssid = choose_network()

    if not ssid:
        print("Error: no se ingresó ningún SSID.", file=sys.stderr)
        sys.exit(1)

    # Security
    security = args.security or choose_security()

    # Password
    if security == "nopass":
        password = ""
    elif args.password is not None:
        password = args.password
    else:
        import getpass
        password = getpass.getpass(f"Contraseña para '{ssid}': ")

    # Output path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_ssid = "".join(c if c.isalnum() or c in "-_" else "_" for c in ssid)
    output = args.output or f"wifi_qr_{safe_ssid}_{timestamp}.png"

    wifi_string = build_wifi_string(ssid, password, security, args.hidden)
    generate_qr_image(wifi_string, ssid, output, include_label=not args.no_label)

    print(f"\nQR generado: {output}")
    print(f"Resolución: 300 DPI — listo para imprimir")


if __name__ == "__main__":
    main()
