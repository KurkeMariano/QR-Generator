/**
 * app.js — WiFi QR Code Generator
 *
 * Generates a WiFi QR code using the standard WIFI: URI format:
 *   WIFI:S:<SSID>;T:<WPA|WEP|nopass>;P:<password>;H:<true|false>;;
 */

(function () {
  "use strict";

  // ── DOM References ──────────────────────────────────────────────────────────
  const form = document.getElementById("wifi-form");
  const ssidInput = document.getElementById("ssid");
  const passwordInput = document.getElementById("password");
  const securitySelect = document.getElementById("security");
  const hiddenCheckbox = document.getElementById("hidden");
  const togglePasswordBtn = document.getElementById("toggle-password");
  const clearBtn = document.getElementById("clear-btn");
  const printBtn = document.getElementById("print-btn");
  const qrSection = document.getElementById("qr-section");
  const qrSsidLabel = document.getElementById("qr-ssid-label");
  const qrCanvasWrapper = document.getElementById("qr-canvas-wrapper");

  // ── Helpers ──────────────────────────────────────────────────────────────────

  /**
   * Escape special characters for the WiFi QR standard.
   * Characters that need escaping: \ ; , " :
   * @param {string} value
   * @returns {string}
   */
  function escapeWifiString(value) {
    return value.replace(/([\\;,":])/g, "\\$1");
  }

  /**
   * Build the WIFI: URI string used in the QR code.
   * @param {string} ssid
   * @param {string} password
   * @param {string} security  - "WPA", "WEP", or "nopass"
   * @param {boolean} hidden
   * @returns {string}
   */
  function buildWifiUri(ssid, password, security, hidden) {
    const escapedSsid = escapeWifiString(ssid);
    const escapedPassword = escapeWifiString(password);
    const hiddenFlag = hidden ? "true" : "false";

    if (security === "nopass") {
      return `WIFI:S:${escapedSsid};T:nopass;P:;H:${hiddenFlag};;`;
    }

    return `WIFI:S:${escapedSsid};T:${security};P:${escapedPassword};H:${hiddenFlag};;`;
  }

  /**
   * Render a new QR code into qrCanvasWrapper.
   * Uses qrcode-generator (MIT, Kazuhiko Arase).
   * @param {string} text
   */
  function renderQRCode(text) {
    qrCanvasWrapper.innerHTML = "";

    // typeNumber 0 = auto-select, H = highest error correction
    var qr = qrcode(0, "H");
    qr.addData(text);
    qr.make();

    // Render as SVG for crisp print quality
    var svgTag = qr.createSvgTag({ scalable: true });
    qrCanvasWrapper.innerHTML = svgTag;

    // Style the SVG so it fits neatly
    var svg = qrCanvasWrapper.querySelector("svg");
    if (svg) {
      svg.setAttribute("width", "220");
      svg.setAttribute("height", "220");
      svg.style.border = "4px solid #fff";
      svg.style.borderRadius = "6px";
      svg.style.boxShadow = "0 0 0 2px #e2e8f0";
    }
  }

  // ── Event Handlers ───────────────────────────────────────────────────────────

  /** Show/hide password field */
  togglePasswordBtn.addEventListener("click", function () {
    const isPassword = passwordInput.type === "password";
    passwordInput.type = isPassword ? "text" : "password";
    togglePasswordBtn.textContent = isPassword ? "🙈" : "👁";
    togglePasswordBtn.setAttribute(
      "aria-label",
      isPassword ? "Ocultar contraseña" : "Mostrar contraseña"
    );
  });

  /** Hide password field when security is "nopass" */
  securitySelect.addEventListener("change", function () {
    const passwordGroup = passwordInput.closest(".form-group");
    if (securitySelect.value === "nopass") {
      passwordGroup.style.display = "none";
      passwordInput.value = "";
    } else {
      passwordGroup.style.display = "";
    }
  });

  /** Generate QR code on form submit */
  form.addEventListener("submit", function (event) {
    event.preventDefault();

    const ssid = ssidInput.value.trim();
    const password = passwordInput.value;
    const security = securitySelect.value;
    const hidden = hiddenCheckbox.checked;

    if (!ssid) {
      ssidInput.focus();
      return;
    }

    const wifiUri = buildWifiUri(ssid, password, security, hidden);

    qrSsidLabel.textContent = ssid;
    renderQRCode(wifiUri);

    qrSection.hidden = false;
    qrSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });

  /** Clear form and hide QR section */
  clearBtn.addEventListener("click", function () {
    form.reset();
    // Ensure password field is shown after reset
    const passwordGroup = passwordInput.closest(".form-group");
    passwordGroup.style.display = "";
    passwordInput.type = "password";
    togglePasswordBtn.textContent = "👁";

    qrSection.hidden = true;
    qrCanvasWrapper.innerHTML = "";
  });

  /** Print the QR card */
  printBtn.addEventListener("click", function () {
    window.print();
  });
})();
