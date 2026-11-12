# com.google.android.googlequicksearchbox — Google (nhận dạng giọng nói)

- Bản 16.24.68.ve.arm64 (vc 301541706); nhập vào hub 2026-11-11, digest khớp APK nguồn.
- Chữ ký không phải key Google release (`7ce83c1b…` vs Google `f0fd6c5b…`) — bản build/mod riêng; cẩn thận khi update upstream.
- Cần permission `RECORD_AUDIO` (nhận dạng giọng nói) — quyền tự cấp cho app system uid, không cần request.
- 238 MB — nặng nhất catalog, chú ý dung lượng khi cài trên HU.
- minSdk 28 — đúng API IHU689G.
- Rollback: gỡ cài đặt thường.
