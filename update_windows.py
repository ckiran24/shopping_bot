from pathlib import Path

root = Path(__file__).resolve().parent
path = root / "bot.py"
source = path.read_text(encoding="utf-8-sig")

old = (
    '    page.pdf(path=str(output / "confirmation.pdf"), print_background=True)\n'
    '    result["confirmation_file"] = "confirmation.pdf"'
)
new = '    result["confirmation_file"] = save_acknowledgement(page, output)'

if old not in source and new not in source:
    raise SystemExit("Unrecognized PDF section. No files changed.")

if "def run(args):" not in source or "def shop(" not in source:
    raise SystemExit("Unrecognized bot structure. No files changed.")

if "from dotenv import load_dotenv" not in source:
    source = source.replace(
        "import sys",
        "import sys\nfrom dotenv import load_dotenv",
        1,
    )

if "from datetime import datetime" not in source:
    source = source.replace(
        "import sys",
        "import sys\nfrom datetime import datetime\nfrom zoneinfo import ZoneInfo",
        1,
    )

helper = '''def save_acknowledgement(page, output):
    button = page.get_by_role("button", name="Generate PDF order", exact=True)
    expect(button).to_be_visible()
    with page.expect_download() as event:
        button.click()

    download = event.value
    failure = download.failure()
    if failure:
        raise ValueError(f"Acknowledgement download failed: {failure}")

    timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y%m%d_%H%M%S_%f")
    filename = f"confirmation_{timestamp}_IST.pdf"
    destination = output / filename
    temporary = destination.with_suffix(".pdf.part")

    try:
        download.save_as(str(temporary))
        with temporary.open("rb") as pdf:
            if pdf.read(5) != b"%PDF-":
                raise ValueError("Acknowledgement download is not a PDF")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)

    return filename'''

if "def save_acknowledgement(" not in source:
    source = source.replace("def shop(", helper + "\n\ndef shop(", 1)

source = source.replace(old, new)

if "def read_credentials(" not in source and "load_dotenv(" not in source:
    source = source.replace(
        "def run(args):",
        'def run(args):\n'
        '    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)',
        1,
    )

source = source.replace(
    "browser.new_page()",
    "browser.new_page(accept_downloads=True)",
)
compile(source, str(path), "exec")

backup = root / "bot.py.before_pdf_update"
if not backup.exists():
    backup.write_bytes(path.read_bytes())
path.write_text(source, encoding="utf-8")

requirements = root / "requirements.txt"
lines = requirements.read_text(encoding="utf-8-sig").splitlines()
for package in ("python-dotenv==1.2.1", "tzdata==2025.3"):
    if not any(line.split("==")[0] == package.split("==")[0] for line in lines):
        lines.append(package)
requirements.write_text("\n".join(lines) + "\n", encoding="utf-8")

example = "SAUCE_USERNAME=standard_user\nSAUCE_PASSWORD=secret_sauce\n"
for name in (".env.example", ".env"):
    file = root / name
    if not file.exists():
        file.write_text(example, encoding="utf-8")

ignore = root / ".gitignore"
ignored = ignore.read_text().splitlines() if ignore.exists() else []
for name in (".env", "*.before_pdf_update"):
    if name not in ignored:
        ignored.append(name)
ignore.write_text("\n".join(ignored) + "\n", encoding="utf-8")

live = root / "tests" / "live" / "test_checkout.py"
if live.exists():
    text = live.read_text(encoding="utf-8-sig")
    text = text.replace(
        '(directory / "confirmation.pdf").read_bytes()',
        '(directory / result["confirmation_file"]).read_bytes()',
    )
    live.write_text(text, encoding="utf-8")

print("Updated. Original bot backed up; existing .env preserved.")