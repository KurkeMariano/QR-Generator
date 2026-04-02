# WiFi QR Generator

Genera un código QR de alta resolución (300 DPI) listo para imprimir, que permite a tus visitas conectarse a tu WiFi con solo escanearlo.

## Uso local

### Instalación
```bash
pip install -r requirements.txt
```

### Modo interactivo (escanea redes disponibles)
```bash
python generate_qr.py
```
El script detecta las redes WiFi cercanas, te muestra la lista y te pide la contraseña. Si la red no aparece, podés ingresarla manualmente.

### Modo por parámetros
```bash
python generate_qr.py --ssid "MiRed" --password "miClave123" --security WPA
```

| Parámetro     | Descripción                              |
|---------------|------------------------------------------|
| `--ssid`      | Nombre de la red WiFi                    |
| `--password`  | Contraseña                               |
| `--security`  | `WPA` (default) · `WEP` · `nopass`       |
| `--hidden`    | Marcar como red oculta                   |
| `--output`    | Ruta del archivo PNG de salida           |
| `--no-label`  | Omitir la etiqueta con el nombre de red  |

---

## Ejecutar desde GitHub Actions

### 1. Configurar secretos y variables en el repositorio

Ir a **Settings → Secrets and variables → Actions**:

| Tipo     | Nombre           | Valor                                        |
|----------|------------------|----------------------------------------------|
| Secret   | `RESEND_API_KEY` | Tu API key de [Resend](https://resend.com)   |
| Secret   | `WIFI_PASSWORD`  | Contraseña de la red WiFi                    |
| Variable | `EMAIL_FROM`     | Dirección remitente verificada en Resend (ej: `qr@tudominio.com`) |

Los destinatarios se leen del archivo [emails.txt](emails.txt) del repositorio (un email por línea).

### 2. Disparar el workflow

Ir a **Actions → Generar y enviar QR WiFi → Run workflow** e ingresar:
- **SSID**: nombre de la red
- **Tipo de seguridad**: WPA / WEP / sin contraseña
- **Red oculta**: sí / no

El workflow genera el QR, lo envía por email a todos los destinatarios configurados y lo deja disponible como artefacto descargable por 30 días.

---

## Envío de email manual

```bash
export RESEND_API_KEY="re_xxxx"
export EMAIL_FROM="qr@tudominio.com"
export EMAIL_RECIPIENTS="persona1@mail.com,persona2@mail.com"
export WIFI_SSID="MiRed"

python send_email.py wifi_qr.png
```

---

## Impresión

El PNG generado tiene 300 DPI. Para impresión óptima:
- Tamaño recomendado: 10×10 cm o mayor
- Podés abrirlo en cualquier visor de imágenes e imprimir a escala real
