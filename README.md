# coon-hub

Catalog app cho **Coon** (app quản lý xe chạy trên head unit IHU689G, Geely
Coolray VN). Repo **public** — Coon fetch trực tiếp không cần token:

```
https://raw.githubusercontent.com/g-e-n-v/coon-hub/main/hub.json
```

Nếu repo quay lại private, mọi xe gãy catalog (404) — đừng làm.

## Cấu trúc

```
hub.json                catalog duy nhất — nguồn sự thật, edit rolling trên main
hub.schema.json         JSON Schema v1 (hợp đồng hình thức; chuẩn kiểm tra là tools/validate.py)
icons/<package>.webp    icon 192px hiển thị trong Coon (extract từ APK gốc)
apps/<package>.md       maintainer notes: vá gì, rủi ro, rollback
tools/validate.py       CI + local: cấu trúc, nghiệp vụ, icon, (tuỳ chọn) digest asset thật
tools/promote.sh        1 lệnh phát hành: check cert → upload → sửa hub.json → validate
.github/workflows/      CI chạy validate.py --assets
```

APK **không commit vào repo** — nằm trên GitHub Releases, tag `hub-YYYY.MM.DD`,
link asset ổn định vĩnh viễn theo tag. Factory APK gốc vẫn backup ở coolray-lab
`extracts/factory-apks/` (Git LFS); hub chỉ chứa digest + URL.

## Schema v1 — hub.json

Nguyên tắc: **mọi field phải phục vụ một quyết định/hiển thị runtime của Coon**.
Thông tin maintainer nằm ở `apps/<package>.md`, không nằm trong catalog.

| Field | Bắt buộc | Ý nghĩa |
| --- | --- | --- |
| `schemaVersion` | ✓ | luôn `1`. Coon từ chối catalog có số cao hơn mức nó hiểu |
| `apps[].package` | ✓ | khóa duy nhất = Android package = tên file icon/doc |
| `apps[].name` | ✓ | hiển thị |
| `apps[].summary` | ✓ | mô tả 1 dòng (HU không có browser — không URL) |
| `apps[].category` | ✓ | `patch \\| maps \\| media \\| utility \\| other` — chỉ để nhóm hiển thị |
| `apps[].icon` | | path tương đối `icons/<file>.webp|.png`; Coon resolve theo base URL catalog |
| `apps[].requires` | | package phải có trước khi dùng. Coon **chỉ cảnh báo**, không chặn cài |
| `apps[].postInstall` | | hook chạy sau cài mới/cập nhật (xem dưới) |
| `apps[].postRollback` | | hook chạy sau "Gỡ cập nhật" (rollback về /system factory) |
| `apps[].factory` | | **có = system app patch**, không có = app thường. `{versionCode, sha256, apk, size}` — digest để Coon detect trạng thái; `apk` để chia sẻ + khôi phục worst-case (mất cả backup Coon lẫn `/system`) |
| `apps[].releases[]` | ✓ | mảng phiên bản, **sort tăng nghiêm ngặt theo versionCode** |
| `releases[].releaseAt` | ✓ | ISO `YYYY-MM-DD`; tối đa 1 release/app/ngày; Coon hiển thị `2026.11.04` |
| `releases[].versionCode` | ✓ | số nguyên thật nằm trong APK (xem quy ước dưới) |
| `releases[].apk` | ✓ | URL tuyệt đối (GitHub Releases asset) |
| `releases[].sha256` | ✓ | digest của file apk — Coon từ chối cài khi sai |
| `releases[].size` | ✓ | byte — progress bar + hiển thị |
| `releases[].notes` | | mảng string — changelog "đã làm gì trong bản này" |

### Quy ước versionCode

- Là số nguyên trong AndroidManifest của chính APK — **không tự chế số**, đọc từ
  APK thật (promote.sh tự tính digest/size; versionCode khai báo qua flag, CI
  verify digest khớp asset).
- **Patch (hub tự build)**: `YYYYMMDDnn` — 10 chữ số, `nn` = 01..99. Luôn lớn
  hơn versionCode factory 8 chữ số kiểu Geely (`26020313` ≈ 26 triệu < ngày
  thuần `20261104` ≈ 20 triệu → phải 10 chữ số) và nhỏ hơn int32 max
  (2.147.483.647 — an toàn tới ~năm 2147). Điều kiện này để "Gỡ cập nhật" =
  uninstall update (PMS tự lộ lại bản `/system`), không cần downgrade.
- **App thường**: chép nguyên versionCode upstream (vd YouTube ReVanced
  `1561068412`).

### Hook `postInstall` / `postRollback`

Theo pattern lifecycle hooks của ngành (npm `postinstall`/`postuninstall`,
Debian `postinst`/`postrm`, Helm `post-install`/`post-rollback` —
<https://helm.sh/docs/topics/charts_hooks/>). **Bộ giá trị đóng, chỉ 2 loại:**

| Giá trị | Ý nghĩa |
| --- | --- |
| `start-service:<ComponentName>` | Coon gọi `startForegroundService()` cho ComponentName đó |
| `reboot` | Coon reboot HU — **hỏi xác nhận trước khi chạy** |

`<ComponentName>` dùng chuẩn Android `package/class` (class bắt đầu bằng `.`
= nối thêm package; parse bằng `ComponentName.unflattenFromString()`), cùng
dạng `am start-activity -n`. Ví dụ:

```json
"postInstall":   ["start-service:com.flyme.auto.keyserver/.service.AutoKeyService"],
"postRollback":  ["start-service:com.flyme.auto.keyserver/.service.AutoKeyService"]
```

Tại sao cần: app system uid 1000 — cài/cập nhật/gỡ update đều khiến PMS kill
toàn bộ uid 1000 (Coon chết giữa chừng, app đích chỉ được đánh thức bởi
broadcast boot). Coon đặt cờ pending **trước** khi commit, AMS hồi sinh Coon,
resume chạy hook tuần tự (dừng ở lỗi đầu). Giá trị lạ → validate.py chặn +
Coon từ chối catalog (fail-closed). Hook là script tự do như npm thì bị ngành
siết lại (npm v12 mặc định tắt) — hub cố tình đóng enum 2 action.

## Phát hành (maintainer)

```bash
# bản vá mới cho app đã đăng ký
tools/promote.sh com.flyme.auto.keyserver ~/path/GeelyAutoKeyServer.apk \
  --version-code 2026110401 \
  --note "map phím 360"

# đăng ký factory base lần đầu (APK gốc pull từ xe)
tools/promote.sh com.flyme.auto.keyserver ~/path/factory.apk \
  --version-code 26020313 --factory

# app thường mới
tools/promote.sh app.revanced.android.youtube ~/path/youtube.apk \
  --version-code 1561068412 \
  --name "YouTube ReVanced" --category media \
  --summary "YouTube không quảng cáo. Cần MicroG RE." \
  --requires app.revanced.android.gms \
  --note "bản đầu"
```

promote.sh tự: check cert platform testkey với patch/factory (serial
`b3998086d056cffa`), tính sha256+size, tạo/upload release asset, sửa hub.json,
chạy validate. Sau đó commit + push như thường — CI phải xanh mới coi release
xong.

Kiểm tra local: `python3 tools/validate.py` (nhanh) hoặc `--assets` (tải APK
verify digest — CI luôn chạy chế độ này).

## Icon

WebP 192px, tên `<package>.webp` (hoặc `.png`), extract từ APK gốc. Icon mồ côi
(không app nào dùng) cũng bị validate.py chặn.
