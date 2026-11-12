#!/usr/bin/env python3
"""Validate hub.json (schema v1) — chuẩn kiểm tra của repo coon-hub.

Thuần stdlib, không cần pip install gì. Chạy local trước khi push; CI chạy
thêm --assets để tải từng APK và verify sha256 + size thật.

Usage:
  tools/validate.py            # cấu trúc + nghiệp vụ + icon tồn tại trong repo
  tools/validate.py --assets   # thêm: tải mọi APK (release + factory), verify digest

Exit code 0 = PASS, khác 0 = có lỗi (in ra từng dòng).
"""

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HUB = REPO / "hub.json"

SUPPORTED_SCHEMA_VERSION = 1
PACKAGE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
URL_RE = re.compile(r"^https://\S+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ICON_RE = re.compile(r"^icons/[^/]+\.((webp)|(png))$")
HOOK_RE = re.compile(r"^start-service:[^/\s]+/[^/\s]+$")
# Trạng thái phát hành: stable = ổn định, beta = đang kiểm thử. Bộ giá trị đóng.
RELEASE_STATUSES = ("stable", "beta")
# Patch versionCode 10 chữ số: YYYYMMDDnn (nn = 01..99, luôn > factory 8 chữ số).
PATCH_VC_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})(\d{2})$")
ASSET_CHUNK = 1 << 20
ASSET_TIMEOUT_S = 300

APP_KEYS = {"package", "name", "summary", "tags", "icon", "requires",
            "postInstall", "postRollback", "factory", "releases"}
FACTORY_KEYS = {"versionCode", "sha256", "apk", "size"}
RELEASE_KEYS = {"releaseAt", "versionCode", "status", "apk", "sha256", "size", "notes"}

errors = []


def err(msg: str) -> None:
    errors.append(msg)


def valid_date(s: str) -> bool:
    m = DATE_RE.match(s)
    if not m:
        return False
    y, mo, d = int(s[0:4]), int(s[5:7]), int(s[8:10])
    try:
        date(y, mo, d)
        return True
    except ValueError:
        return False


def valid_patch_version_code(vc, where: str) -> None:
    """Patch release phải mã hoá ngày: YYYYMMDDnn — để luôn > factory 8 chữ số."""
    m = PATCH_VC_RE.match(str(vc))
    if not m:
        err(f"{where}: versionCode patch phải là 10 chữ số YYYYMMDDnn, được {vc}")
        return
    y, mo, d, nn = (int(g) for g in m.groups())
    if nn < 1 or nn > 99:
        err(f"{where}: phần nn của versionCode phải 01..99, được {nn:02d}")
    try:
        date(y, mo, d)
    except ValueError:
        err(f"{where}: versionCode patch mã hoá ngày không hợp lệ: {y:04d}-{mo:02d}-{d:02d}")


def check_hook_list(hooks, where: str) -> None:
    if hooks is None:
        return
    if not isinstance(hooks, list):
        err(f"{where}: phải là mảng string")
        return
    for i, h in enumerate(hooks):
        if h == "reboot":
            continue
        if isinstance(h, str) and HOOK_RE.match(h):
            continue
        err(f"{where}[{i}]: giá trị không hợp lệ ({h!r}) — chỉ 'reboot' hoặc 'start-service:<package>/<class>'")


def check_app(idx: int, app, icon_seen: set) -> None:
    where = f"apps[{idx}]"
    if not isinstance(app, dict):
        err(f"{where}: phải là object")
        return
    pkg = app.get("package")
    where = f"apps[{idx}] ({pkg})"

    unknown = set(app) - APP_KEYS
    if unknown:
        err(f"{where}: field lạ: {sorted(unknown)} (cho phép: {sorted(APP_KEYS)})")

    if not isinstance(pkg, str) or not PACKAGE_RE.match(pkg or ""):
        err(f"{where}: package thiếu/sai định dạng Android package")

    name = app.get("name")
    if not isinstance(name, str) or not name.strip():
        err(f"{where}: name phải là chuỗi không rỗng")

    if not isinstance(app.get("summary"), str):
        err(f"{where}: summary phải là chuỗi")

    tags = app.get("tags")
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        err(f"{where}: tags phải là mảng string")

    icon = app.get("icon")
    if icon is not None:
        if not isinstance(icon, str) or not ICON_RE.match(icon):
            err(f"{where}: icon phải dạng 'icons/<file>.webp|.png', được {icon!r}")
        elif not (REPO / icon).is_file():
            err(f"{where}: icon không tồn tại trong repo: {icon}")
        else:
            icon_seen.add(icon)

    req = app.get("requires")
    if req is not None:
        if not isinstance(req, list) or not all(
            isinstance(r, str) and PACKAGE_RE.match(r) for r in req
        ):
            err(f"{where}: requires phải là mảng Android package")
        elif len(set(req)) != len(req):
            err(f"{where}: requires có phần tử trùng")

    check_hook_list(app.get("postInstall"), f"{where}.postInstall")
    check_hook_list(app.get("postRollback"), f"{where}.postRollback")

    factory = app.get("factory")
    if factory is not None:
        if not isinstance(factory, dict):
            err(f"{where}.factory: phải là object")
            factory = None
        else:
            fwhere = f"{where}.factory"
            funknown = set(factory) - FACTORY_KEYS
            if funknown:
                err(f"{fwhere}: field lạ: {sorted(funknown)}")
            for k in ("versionCode", "sha256", "apk", "size"):
                if k not in factory:
                    err(f"{fwhere}: thiếu field bắt buộc {k}")
            vc = factory.get("versionCode")
            if not isinstance(vc, int) or isinstance(vc, bool) or vc < 1:
                err(f"{fwhere}.versionCode phải là số nguyên > 0")
            if not SHA256_RE.match(factory.get("sha256") or ""):
                err(f"{fwhere}.sha256 phải là 64 ký tự hex thường")
            if not URL_RE.match(factory.get("apk") or ""):
                err(f"{fwhere}.apk phải là URL https")
            sz = factory.get("size")
            if not isinstance(sz, int) or isinstance(sz, bool) or sz < 0:
                err(f"{fwhere}.size phải là số nguyên >= 0")

    releases = app.get("releases")
    if not isinstance(releases, list):
        err(f"{where}: releases phải là mảng")
        return

    prev_vc = None
    seen_dates = set()
    for i, rel in enumerate(releases):
        rwhere = f"{where}.releases[{i}]"
        if not isinstance(rel, dict):
            err(f"{rwhere}: phải là object")
            continue
        runknown = set(rel) - RELEASE_KEYS
        if runknown:
            err(f"{rwhere}: field lạ: {sorted(runknown)}")
        for k in ("releaseAt", "versionCode", "status", "apk", "sha256", "size"):
            if k not in rel:
                err(f"{rwhere}: thiếu field bắt buộc {k}")

        status = rel.get("status")
        if status not in RELEASE_STATUSES:
            err(f"{rwhere}.status phải là {' hoặc '.join(RELEASE_STATUSES)}, được {status!r}")

        ra = rel.get("releaseAt")
        if not isinstance(ra, str) or not valid_date(ra):
            err(f"{rwhere}.releaseAt phải là ngày ISO YYYY-MM-DD hợp lệ, được {ra!r}")
        elif ra in seen_dates:
            err(f"{rwhere}.releaseAt={ra} trùng release khác của app (tối đa 1 release/app/ngày)")
        else:
            seen_dates.add(ra)

        vc = rel.get("versionCode")
        if not isinstance(vc, int) or isinstance(vc, bool) or vc < 1:
            err(f"{rwhere}.versionCode phải là số nguyên > 0")
        elif prev_vc is not None and vc <= prev_vc:
            err(f"{rwhere}.versionCode={vc} không tăng so với release trước ({prev_vc}) — releases phải sort tăng nghiêm ngặt")
        else:
            prev_vc = vc

        if not URL_RE.match(rel.get("apk") or ""):
            err(f"{rwhere}.apk phải là URL https")
        if not SHA256_RE.match(rel.get("sha256") or ""):
            err(f"{rwhere}.sha256 phải là 64 ký tự hex thường")
        sz = rel.get("size")
        if not isinstance(sz, int) or isinstance(sz, bool) or sz < 0:
            err(f"{rwhere}.size phải là số nguyên >= 0")

        notes = rel.get("notes")
        if notes is not None and (
            not isinstance(notes, list)
            or not all(isinstance(n, str) and n.strip() for n in notes)
        ):
            err(f"{rwhere}.notes phải là mảng chuỗi không rỗng")

        if factory is not None:
            if isinstance(vc, int) and vc <= factory.get("versionCode", 0):
                err(f"{rwhere}: versionCode patch ({vc}) phải > factory.versionCode ({factory.get('versionCode')}) — điều kiện rollback qua uninstall")
            valid_patch_version_code(vc, rwhere)


def check_assets(root) -> None:
    """Tải từng APK (release + factory), verify sha256 + size với catalog."""
    urls = []
    for app in root.get("apps", []):
        if not isinstance(app, dict):
            continue
        pkg = app.get("package", "?")
        fac = app.get("factory")
        if isinstance(fac, dict) and URL_RE.match(fac.get("apk") or ""):
            urls.append((f"{pkg} [factory]", fac["apk"], fac.get("sha256"), fac.get("size")))
        for i, rel in enumerate(app.get("releases") or []):
            if isinstance(rel, dict) and URL_RE.match(rel.get("apk") or ""):
                urls.append((f"{pkg} releases[{i}]", rel["apk"], rel.get("sha256"), rel.get("size")))

    for label, url, want_sha, want_size in urls:
        print(f"[asset] {label}: {url}")
        try:
            h = hashlib.sha256()
            got = 0
            req = urllib.request.Request(url, headers={"User-Agent": "coon-hub-validate"})
            with urllib.request.urlopen(req, timeout=ASSET_TIMEOUT_S) as resp:
                while True:
                    chunk = resp.read(ASSET_CHUNK)
                    if not chunk:
                        break
                    h.update(chunk)
                    got += len(chunk)
        except Exception as e:  # noqa: BLE001 - báo mọi lỗi mạng rồi exit khác 0
            err(f"[asset] {label}: tải thất bại: {e}")
            continue
        if want_sha and h.hexdigest() != want_sha:
            err(f"[asset] {label}: sha256 không khớp (catalog {want_sha}, thật {h.hexdigest()})")
        if isinstance(want_size, int) and got != want_size:
            err(f"[asset] {label}: size không khớp (catalog {want_size}, thật {got})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--assets", action="store_true",
                    help="tải mọi APK và verify sha256 + size thật")
    ap.add_argument("file", nargs="?", default=str(HUB),
                    help="đường dẫn catalog (mặc định hub.json ở gốc repo)")
    args = ap.parse_args()

    path = Path(args.file)
    try:
        root = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"FAIL: đọc {path}: {e}")
        return 1

    if not isinstance(root, dict):
        err("gốc catalog phải là object")

    unknown = set(root if isinstance(root, dict) else {}) - {"schemaVersion", "apps"}
    if unknown:
        err(f"field lạ ở gốc: {sorted(unknown)}")

    sv = root.get("schemaVersion")
    if sv != SUPPORTED_SCHEMA_VERSION:
        err(f"schemaVersion phải đúng {SUPPORTED_SCHEMA_VERSION}, được {sv!r} — Coon chỉ hiểu schema v{SUPPORTED_SCHEMA_VERSION}")

    apps = root.get("apps")
    if not isinstance(apps, list):
        err("apps phải là mảng")
        apps = []

    seen_pkgs = set()
    icon_seen = set()
    for idx, app in enumerate(apps):
        check_app(idx, app, icon_seen)
        pkg = app.get("package") if isinstance(app, dict) else None
        if pkg in seen_pkgs:
            err(f"apps[{idx}] ({pkg}): package trùng lặp")
        seen_pkgs.add(pkg)

    for p in sorted((REPO / "icons").glob("*")):
        if p.name.startswith("."):
            continue
        rel = f"icons/{p.name}"
        if rel not in icon_seen:
            err(f"icon mồ côi không app nào dùng: {rel}")

    if args.assets:
        check_assets(root)

    if errors:
        print(f"FAIL — {len(errors)} lỗi:")
        for e in errors:
            print(f"  - {e}")
        return 1
    n_rel = sum(len(a.get("releases") or []) for a in apps if isinstance(a, dict))
    print(f"PASS — {len(apps)} app, {n_rel} release" + (" (đã verify asset)" if args.assets else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
