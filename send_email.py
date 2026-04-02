#!/usr/bin/env python3
"""
Sends the WiFi QR code image via Resend to a list of recipients.
"""

import os
import sys
import base64
import requests


RESEND_API_URL = "https://api.resend.com/emails"


def send_qr_email(
    api_key: str,
    from_address: str,
    recipients: list[str],
    ssid: str,
    image_path: str,
) -> None:
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()

    filename = os.path.basename(image_path)

    payload = {
        "from": from_address,
        "to": recipients,
        "subject": f"QR WiFi — Red: {ssid}",
        "html": f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: auto;">
            <h2 style="color: #333;">Código QR para conectarse al WiFi</h2>
            <p>Escaneá el QR adjunto para conectarte a la red <strong>{ssid}</strong>.</p>
            <p>También podés imprimir la imagen adjunta y pegarla donde sea visible para tus visitas.</p>
            <hr style="border: none; border-top: 1px solid #ddd;">
            <p style="color: #888; font-size: 12px;">Generado automáticamente · QR-Generator</p>
        </div>
        """,
        "attachments": [
            {
                "filename": filename,
                "content": image_b64,
            }
        ],
    }

    response = requests.post(
        RESEND_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )

    if response.status_code not in (200, 201):
        print(f"Error al enviar email: {response.status_code} — {response.text}", file=sys.stderr)
        sys.exit(1)

    print(f"Email enviado a: {', '.join(recipients)}")


def main():
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        print("Error: variable de entorno RESEND_API_KEY no definida.", file=sys.stderr)
        sys.exit(1)

    from_address = os.environ.get("EMAIL_FROM")
    if not from_address:
        print("Error: variable de entorno EMAIL_FROM no definida.", file=sys.stderr)
        sys.exit(1)

    emails_file = os.path.join(os.path.dirname(__file__), "emails.txt")
    if not os.path.isfile(emails_file):
        print(f"Error: no se encontró el archivo {emails_file}", file=sys.stderr)
        sys.exit(1)

    with open(emails_file, "r") as f:
        recipients = [line.strip() for line in f if line.strip()]

    if not recipients:
        print(f"Error: {emails_file} no contiene ninguna dirección.", file=sys.stderr)
        sys.exit(1)

    ssid = os.environ.get("WIFI_SSID", "WiFi")

    # Find the generated QR image (passed as first argument or auto-detected)
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # Look for the most recent QR image in the current directory
        import glob
        files = sorted(glob.glob("wifi_qr_*.png"), reverse=True)
        if not files:
            print("Error: no se encontró ningún archivo wifi_qr_*.png.", file=sys.stderr)
            sys.exit(1)
        image_path = files[0]

    if not os.path.isfile(image_path):
        print(f"Error: archivo no encontrado: {image_path}", file=sys.stderr)
        sys.exit(1)

    send_qr_email(api_key, from_address, recipients, ssid, image_path)


if __name__ == "__main__":
    main()
