# QR Generator — WiFi QR Code

Una aplicación web que genera códigos QR para conectarse a redes WiFi. Ideal para imprimir en papel y dejar en la mesa para que las visitas puedan conectarse fácilmente.

## Características

- 📶 Genera un código QR con los datos de tu red WiFi
- 🔒 Soporta redes WPA/WPA2/WPA3, WEP y redes abiertas
- 🙈 Redes ocultas (hidden)
- 🖨️ Botón de impresión — solo imprime el código QR, sin el formulario
- 🔐 Todo se procesa en tu navegador; ningún dato se envía a servidores externos

## Cómo usar

1. Abrí `index.html` en tu navegador
2. Completá el nombre de la red (SSID), la contraseña y el tipo de seguridad
3. Hacé clic en **Generar QR**
4. Hacé clic en **🖨️ Imprimir** para imprimirlo en papel

## Formato del QR

El código QR usa el estándar WiFi URI reconocido por iOS (11+) y Android:

```
WIFI:S:<SSID>;T:<WPA|WEP|nopass>;P:<contraseña>;H:<true|false>;;
```

## Dependencias

- [`qrcode-generator`](https://github.com/kazuhikoarase/qrcode-generator) — MIT License, Kazuhiko Arase
