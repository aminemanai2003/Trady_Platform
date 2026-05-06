"""CLI test for POST /api/ocr/extract/ — runs against all test images."""
import json
import pathlib
import urllib.request
import uuid

ENDPOINT = "http://localhost:8000/api/ocr/extract/"

TEST_IMAGES = [
    (r"C:\Users\amine\Desktop\Projet DS\1test.png",   "Lithuanian ID card"),
    (r"C:\Users\amine\Desktop\Projet DS\cin_tn.HEIC", "Tunisian CIN (HEIC)"),
]


_MIME_MAP = {
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
}


def test_image(image_path: str, label: str) -> None:
    path = pathlib.Path(image_path)
    if not path.exists():
        print(f"[SKIP] {label}: file not found at {image_path}\n")
        return

    img_bytes = path.read_bytes()
    boundary  = uuid.uuid4().hex.encode()
    mime      = _MIME_MAP.get(path.suffix.lower(), "image/jpeg")

    body = (
        b"--" + boundary + b"\r\n"
        b'Content-Disposition: form-data; name="image"; filename="' + path.name.encode() + b'"\r\n'
        b"Content-Type: " + mime.encode() + b"\r\n\r\n"
        + img_bytes
        + b"\r\n--" + boundary + b"--\r\n"
    )

    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={"Content-Type": "multipart/form-data; boundary=" + boundary.decode()},
    )

    print(f"\n{'=' * 60}")
    print(f"TEST: {label}  ({path.name}, {len(img_bytes):,} bytes)")
    print(f"{'=' * 60}")

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
    except urllib.request.HTTPError as exc:
        print(f"  HTTP {exc.code}: {exc.read().decode()}")
        return
    except Exception as exc:
        print(f"  ERROR: {exc}")
        return

    fields = {
        "Full name":       f"{data.get('first_name','')} {data.get('last_name','')}".strip() or "—",
        "Document number": data.get("id_number",     "—"),
        "Nationality":     data.get("nationality",   "—"),
        "Date of birth":   data.get("date_of_birth", "—"),
        "Expiry date":     data.get("expiry_date",   "—"),
        "Confidence":      data.get("confidence",    0),
        "Issues":          data.get("issues",        {}),
    }
    print("EXTRACTED FIELDS")
    for k, v in fields.items():
        print(f"  {k:<20} {v}")

    print("\nRAW OCR TEXT")
    print(data.get("raw_ocr_text", "(empty)"))


if __name__ == "__main__":
    print("OCR pipeline test — Django must be running on http://localhost:8000")
    print("First run loads EasyOCR models (~30 s)...")
    for img, lbl in TEST_IMAGES:
        test_image(img, lbl)
    print("\nDone.")
