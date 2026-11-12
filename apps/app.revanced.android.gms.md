# app.revanced.android.gms — MicroG RE

- Bản 7.3.0 (vc 255070304); nhập vào hub 2026-11-11, digest khớp APK nguồn.
- Chữ ký: key riêng của MicroG RE (không phải platform) — app thường, cài/gỡ như app user.
- Nên bật **whitelist pin** cho MicroG sau khi cài (đừng để bị kill nền).
- Là dependency bắt buộc của `app.revanced.android.youtube` (catalog khai báo `requires`).
- Rollback: gỡ cài đặt thường. Gỡ MicroG làm gãy YouTube ReVanced + Google Maps Morphe (nếu có cài).
