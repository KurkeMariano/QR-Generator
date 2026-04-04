# WiFi QR Generator

Genera un código QR listo para imprimir en formato **tarjeta de crédito (85.6 × 54 mm)**, PDF o PNG a 300 DPI. Tus visitas se conectan al WiFi con solo escanearlo.

---

## Requisitos previos

- Python 3.10 o superior
- Las dependencias del proyecto

```bash
pip install -r requirements.txt
```

---

## Uso local

### Modo interactivo (recomendado)

Ejecutá el script sin parámetros. En WSL/Linux detecta automáticamente las redes WiFi cercanas usando el adaptador de red de Windows:

```bash
python3 generate_qr.py
```

El script te muestra las redes disponibles, te pide la contraseña y genera un PNG. Si la red no aparece en la lista, podés ingresarla manualmente.

### Modo por parámetros

```bash
python3 generate_qr.py --ssid "MiRed" --password "miClave123" --security WPA
```

---

## Opciones disponibles

### Red WiFi principal

| Parámetro | Descripción | Ejemplo |
|---|---|---|
| `--ssid` | Nombre de la red | `--ssid "MiCasa"` |
| `--password` | Contraseña | `--password "abc123"` |
| `--security` | Tipo de cifrado: `WPA` (default) · `WEP` · `nopass` | `--security WPA` |
| `--hidden` | Marcar la red como oculta | `--hidden` |

### Segunda red (modo dual)

Genera una imagen con dos tarjetas apiladas: red principal arriba, red de invitados abajo.

| Parámetro | Descripción |
|---|---|
| `--ssid2` | Nombre de la segunda red |
| `--password2` | Contraseña de la segunda red |
| `--security2` | Tipo de cifrado de la segunda red |

### Tipo de QR

| Parámetro | Descripción | Ejemplo |
|---|---|---|
| `--type wifi` | QR de red WiFi (default) | |
| `--type url` | QR de URL | `--type url --data "https://ejemplo.com"` |
| `--type text` | QR de texto libre | `--type text --data "Contraseña: abc123"` |
| `--data` | Dato a codificar para `--type url` o `--type text` | |

### Apariencia

| Parámetro | Descripción | Ejemplo |
|---|---|---|
| `--logo` | Imagen de logo para centrar en el QR | `--logo logo.png` |
| `--fg-color` | Color del QR | `--fg-color "#003366"` |
| `--bg-color` | Color de fondo | `--bg-color "#f0f0f0"` |

### Salida

| Parámetro | Descripción |
|---|---|
| `--pdf` | Genera PDF tamaño tarjeta de crédito (85.6 × 54 mm, landscape) |
| `--svg` | Genera SVG vectorial (solo el QR, sin layout de tarjeta) |
| `--output` | Ruta del archivo de salida |
| `--no-label` | Omitir la etiqueta con el nombre de red (solo PNG sin tarjeta) |
| `--preview` | Mostrar el QR en la terminal antes de guardar |

---

## Ejemplos

### PDF para imprimir y recortar (tamaño tarjeta de crédito)

```bash
python3 generate_qr.py --ssid "MiCasa" --password "abc123" --pdf
```

### Escaneo automático de redes + PDF

```bash
python3 generate_qr.py --pdf
```

El script escanea las redes disponibles, elegís la tuya de la lista y genera el PDF.

### Red principal + red de invitados en un solo PDF

```bash
python3 generate_qr.py \
  --ssid "MiCasa" --password "clave1" \
  --ssid2 "MiCasa_Guest" --password2 "clave2" \
  --pdf
```

Genera una imagen con dos tarjetas apiladas, lista para imprimir y recortar.

### Con logo y colores personalizados

```bash
python3 generate_qr.py --ssid "MiCasa" --password "clave1" --pdf \
  --logo logo.png --fg-color "#003366" --bg-color "#ffffff"
```

El logo queda centrado en el QR. Se usa corrección de error alta (30% de tolerancia) para que el código siga siendo legible.

### Vista previa en la terminal antes de guardar

```bash
python3 generate_qr.py --ssid "MiCasa" --password "clave1" --preview --pdf
```

### QR de URL en SVG

```bash
python3 generate_qr.py --type url --data "https://ejemplo.com" --svg
```

### QR de texto libre

```bash
python3 generate_qr.py --type text --data "Contraseña sala: 4521"
```

---

## Configuración persistente

El script recuerda el último SSID y tipo de seguridad usados en `~/.config/qr-generator/config.json`. La próxima vez que lo ejecutés sin parámetros, los muestra como valores por defecto.

---

## Impresión

El formato recomendado para imprimir es `--pdf`. Genera un archivo en tamaño tarjeta de crédito (85.6 × 54 mm) a 300 DPI, landscape. Imprimí a tamaño real y recortá.

Para el modo dual (dos redes), el PDF mide el doble de alto (~110 mm). Imprimí a tamaño real y recortá cada tarjeta por separado.

---

## Ejecutar desde GitHub Actions

### 1. Configurar secretos y variables en el repositorio

Ir a **Settings → Secrets and variables → Actions**:

| Tipo | Nombre | Valor |
|---|---|---|
| Secret | `RESEND_API_KEY` | Tu API key de [Resend](https://resend.com) |
| Secret | `WIFI_PASSWORD` | Contraseña de la red WiFi |
| Variable | `EMAIL_FROM` | Dirección remitente verificada en Resend (ej: `qr@tudominio.com`) |

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

python3 send_email.py wifi_qr.png
```
