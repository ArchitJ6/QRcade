"""
HTML → GZIP → Base64 → Self-Extracting Loader → QR Code
------------------------------------------------------

This tool compresses ANY HTML file (games, apps, webpages) into a
GZIP-encoded Base64 payload and wraps it in a tiny self-extracting
JavaScript loader using the browser's native DecompressionStream.

The output can be embedded into a QR code so the full HTML page loads
directly after scanning — no server required.

Outputs:
• /<name>/self_extracting.html  → standalone loader HTML
• /<name>/data_uri.txt          → base64 data URI suitable for QR
• /<name>/qr.png                → QR code image (if size allows)

Maximum QR payload target: Version-40 Low ECC ≈ 2953 bytes
"""

import base64
import gzip
import qrcode
import re
from pathlib import Path
import os
import argparse

# ========= Configuration =========
INPUT_FILE = "games/FlappyBird.html"   # Any HTML file can be used

parser = argparse.ArgumentParser(description="Convert HTML to QR self-extracting loader")
parser.add_argument("input_file", nargs="?", default="games/FlappyBird.html", help="Input HTML file")
args = parser.parse_args()

if args.input_file:
    INPUT_FILE = args.input_file

if not os.path.exists(INPUT_FILE):
    print(f"Input file '{INPUT_FILE}' does not exist.")
    exit(1)

os.makedirs("outputs", exist_ok=True)

os.makedirs(f"outputs/{Path(INPUT_FILE).stem}", exist_ok=True)
OUTPUT_QR = f"outputs/{Path(INPUT_FILE).stem}/qr.png"
MAX_QR_BYTES = 2953  # Approx capacity of QR Version 40-L (largest type)
# =================================


def minify_html(html: str) -> str:
    """
    Minify HTML to reduce QR payload size.
    Removes comments and unnecessary whitespace between tags.
    """
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    html = re.sub(r">\s+<", "><", html)
    html = re.sub(r"\s{2,}", " ", html)
    return html.strip()


def compress_html(html: str) -> str:
    """
    GZIP-compress and Base64-encode the HTML.
    Browsers can natively decompress via DecompressionStream.
    """
    compressed = gzip.compress(html.encode("utf-8"), compresslevel=9)
    return base64.b64encode(compressed).decode("ascii")


def make_loader(b64_data: str) -> str:
    """
    Create a minimal self-extracting HTML loader.
    It decodes Base64 → decompresses GZIP → writes HTML into the document.

    Total size ~230 bytes after minification, ideal for QR constraints.
    """
    return (
        "<script type=module>"
        "document.open();"
        "document.write(await new Response("
        "new Response(Uint8Array.from(atob('" + b64_data + "'),c=>c.charCodeAt(0))).body"
        ".pipeThrough(new DecompressionStream('gzip'))"
        ").text());"
        "document.close();"
        "</script>"
    )


def make_data_uri(html: str) -> str:
    """
    Convert loader HTML into a Base64 data URI.
    This string is what's embedded into the QR code.
    """
    return "data:text/html;base64," + base64.b64encode(html.encode()).decode("ascii")


def generate_qr(uri: str, filename: str):
    """
    Generate a QR code image for the given data URI.
    The QR version scales automatically based on content size.
    """
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)
    print(f"✅ QR code saved → {filename}")
    print(f"   QR version: {qr.version}  |  Payload length: {len(uri)} bytes")


def main():
    print("📦 HTML → QR Self-Extracting Converter")
    print("=" * 50)

    # ---- Step 1: Load & Minify ----
    html = Path(INPUT_FILE).read_text(encoding="utf-8")
    html_min = minify_html(html)
    print(f"Original size: {len(html)} bytes")
    print(f"Minified size: {len(html_min)} bytes")

    # ---- Step 2: Compress ----
    compressed_b64 = compress_html(html_min)
    print(f"Compressed size (gzip+base64): {len(compressed_b64)} bytes")

    # ---- Step 3: Create loader ----
    loader_html = make_loader(compressed_b64)
    data_uri = make_data_uri(loader_html)
    print(f"Final loader size (data URI): {len(data_uri)} bytes")

    # ---- Step 4: Capacity Check ----
    if len(data_uri) > MAX_QR_BYTES:
        print("⚠️  Warning: Data exceeds v40 QR capacity (~2953 bytes).")
        print("   The loader still works, but QR may not encode fully.")
    else:
        print("✅ Content fits within a single v40-L QR code.")

    # ---- Step 5: Save Artifacts ----
    Path(f"outputs/{Path(INPUT_FILE).stem}/self_extracting.html").write_text(loader_html, encoding="utf-8")
    Path(f"outputs/{Path(INPUT_FILE).stem}/data_uri.txt").write_text(data_uri, encoding="utf-8")
    print(f"💾 Files saved: outputs/{Path(INPUT_FILE).stem}/self_extracting.html, outputs/{Path(INPUT_FILE).stem}/data_uri.txt")

    # ---- Step 6: Generate QR ----
    try:
        generate_qr(data_uri, OUTPUT_QR)
    except ValueError as e:
        print(f"⚠️ QR generation failed: {e}")
        print("   (Payload may be too large to encode.)")

    print("\n✨ Done! Scan QR to launch your HTML instantly.")

if __name__ == "__main__":
    main()
