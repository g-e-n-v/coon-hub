#!/usr/bin/env bash
#
# Phát hành lên coon-hub: check cert (patch) → upload GitHub Releases →
# sửa hub.json → tools/validate.py. Xem README.md để biết đầy đủ quy ước.
#
# Ví dụ:
#   tools/promote.sh com.flyme.auto.keyserver ./KeyServer-patched.apk \
#       --version-code 2026110401 --note "map phím 360"
#
#   tools/promote.sh com.flyme.auto.keyserver ./KeyServer-factory.apk \
#       --version-code 26020313 --factory
#
#   tools/promote.sh app.revanced.android.youtube ./youtube.apk \
#       --version-code 1561068412 \
#       --name "YouTube ReVanced" --tag media --summary "Không quảng cáo." \
#       --requires app.revanced.android.gms --note "bản đầu"

set -euo pipefail

REPO_SLUG="g-e-n-v/coon-hub"
# AOSP platform testkey (serial B3998086D056CFFA) — khớp firmware HU; APK vá
# hệ thống phải ký đúng key này thì PMS mới nhận là update của system app.
PLATFORM_CERT_SERIAL="b3998086d056cffa"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HUB_JSON="$ROOT/hub.json"

die() { echo "LỖI: $*" >&2; exit 1; }

usage() {
  sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
}

[[ $# -ge 2 ]] || usage
PKG="$1"; shift
APK="$1"; shift

VERSION_CODE=""
RELEASE_AT="$(date +%Y-%m-%d)"
NAME=""
SUMMARY=""
FACTORY=0
declare -a TAGS=() NOTES=() REQUIRES=() POST_INSTALL=() POST_ROLLBACK=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version-code)  VERSION_CODE="$2"; shift 2 ;;
    --release-at)    RELEASE_AT="$2"; shift 2 ;;
    --name)          NAME="$2"; shift 2 ;;
    --tag)           TAGS+=("$2"); shift 2 ;;
    --summary)       SUMMARY="$2"; shift 2 ;;
    --note)          NOTES+=("$2"); shift 2 ;;
    --requires)      REQUIRES+=("$2"); shift 2 ;;
    --post-install)  POST_INSTALL+=("$2"); shift 2 ;;
    --post-rollback) POST_ROLLBACK+=("$2"); shift 2 ;;
    --factory)       FACTORY=1; shift ;;
    *)               echo "Flag lạ: $1" >&2; usage ;;
  esac
done

[[ "$PKG" =~ ^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$ ]] || die "package sai định dạng: $PKG"
[[ -f "$APK" ]] || die "không tìm thấy APK: $APK"
[[ "$VERSION_CODE" =~ ^[0-9]+$ ]] || die "cần --version-code <số nguyên> (bắt buộc)"
command -v gh >/dev/null || die "thiếu 'gh' (brew install gh; gh auth login)"
command -v python3 >/dev/null || die "thiếu python3"
gh auth status >/dev/null 2>&1 || die "chưa 'gh auth login'"

SHA="$(shasum -a 256 "$APK" | awk '{print $1}')"
SIZE="$(stat -f%z "$APK")"

# App đã có trong catalog? Có factory (patch) chưa?
read -r EXISTS HAS_FACTORY < <(python3 - "$HUB_JSON" "$PKG" <<'PY'
import json, sys
apps = json.load(open(sys.argv[1]))["apps"]
pkg = sys.argv[2]
a = next((x for x in apps if x.get("package") == pkg), None)
print(f"{int(a is not None)} {int(a is not None and 'factory' in a)}")
PY
)
IS_PATCH=$(( FACTORY ? 1 : HAS_FACTORY ))

# Patch/factory phải ký platform testkey — chặn phát hành APK ký sai key.
if [[ $IS_PATCH -eq 1 ]]; then
  command -v keytool >/dev/null || die "thiếu keytool (brew install openjdk@17)"
  keytool -printcert -jarfile "$APK" 2>/dev/null | grep -qi "$PLATFORM_CERT_SERIAL" \
    || die "APK không ký platform testkey (serial $PLATFORM_CERT_SERIAL) — từ chối phát hành patch/factory"
fi

# Tạo app entry mới nếu cần.
if [[ $EXISTS -eq 0 ]]; then
  [[ -n "$NAME" ]] || die "app mới: cần --name"
fi

TAG="hub-$(python3 -c "import sys;print(sys.argv[1].replace('-','.'))" "$RELEASE_AT")"
if [[ $FACTORY -eq 1 ]]; then
  ASSET="${PKG}-factory-${VERSION_CODE}.apk"
else
  ASSET="${PKG}-${VERSION_CODE}.apk"
fi
URL="https://github.com/${REPO_SLUG}/releases/download/${TAG}/${ASSET}"

gh release view "$TAG" --repo "$REPO_SLUG" >/dev/null 2>&1 \
  || gh release create "$TAG" --repo "$REPO_SLUG" --title "$TAG" --notes "Hub release $TAG"
gh release upload "$TAG" "$APK#$ASSET" --repo "$REPO_SLUG" --clobber

python3 - "$HUB_JSON" "$PKG" "$VERSION_CODE" "$RELEASE_AT" "$URL" "$SHA" "$SIZE" \
  "$FACTORY" "$NAME" "$SUMMARY" \
  "${NOTES[*]-}" "${REQUIRES[*]-}" "${POST_INSTALL[*]-}" "${POST_ROLLBACK[*]-}" "${TAGS[@]}" <<'PY'
import json, sys

(path, pkg, vc, release_at, url, sha, size,
 factory, name, summary,
 notes, requires, post_install, post_rollback) = sys.argv[1:15]
tags = sys.argv[15:]
vc, size, factory = int(vc), int(size), int(factory)
notes = [s for s in notes.split("|") if s]
requires = [s for s in requires.split("|") if s]
post_install = [s for s in post_install.split("|") if s]
post_rollback = [s for s in post_rollback.split("|") if s]

doc = json.load(open(path, encoding="utf-8"))
apps = doc["apps"]
app = next((a for a in apps if a.get("package") == pkg), None)

if app is None:
    app = {
        "package": pkg,
        "name": name,
        "summary": summary or "",
        "tags": tags,
        "releases": [],
    }
    if requires:
        app["requires"] = requires
    if post_install:
        app["postInstall"] = post_install
    if post_rollback:
        app["postRollback"] = post_rollback
    apps.append(app)
else:
    if name:
        app["name"] = name
    if tags:
        app["tags"] = tags
    if summary:
        app["summary"] = summary
    if requires:
        app["requires"] = requires
    if post_install:
        app["postInstall"] = post_install
    if post_rollback:
        app["postRollback"] = post_rollback

if factory:
    app["factory"] = {"versionCode": vc, "sha256": sha, "apk": url, "size": size}
else:
    if any(r["versionCode"] == vc for r in app["releases"]):
        sys.exit(f"LỖI: {pkg} đã có release versionCode={vc}")
    if any(r["releaseAt"] == release_at for r in app["releases"]):
        sys.exit(f"LỖI: {pkg} đã có release ngày {release_at} (tối đa 1 release/app/ngày)")
    rel = {"releaseAt": release_at, "versionCode": vc, "apk": url, "sha256": sha, "size": size}
    if notes:
        rel["notes"] = notes
    app["releases"].append(rel)
    app["releases"].sort(key=lambda r: r["versionCode"])

apps.sort(key=lambda a: a["package"])
with open(path, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(f"hub.json: đã ghi {pkg} (versionCode={vc}, {'factory' if factory else 'release'})")
PY

echo "Đã upload: $URL"
echo "Chạy validate..."
python3 "$ROOT/tools/validate.py"
echo "Xong. Giờ: git add -A && git commit -m 'hub: $PKG $VERSION_CODE' && git push"
