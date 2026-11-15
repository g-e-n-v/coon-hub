# app.revanced.android.youtube — YouTube ReVanced

- Bản hiện tại: 20.14.43 (vc 1553866176), patches 5.46.0 theo tên APK nguồn; nhập vào hub 2026-11-15.
- Nguồn: `apks/youtube-revanced_v20.14.43-patches_v5.46.0.apk` do người duy trì cung cấp; package, versionCode và minSdk được đọc từ manifest.
- SHA-256: `11083bc6b0ebb371d049acf2d2e1f1c2ce1a9f6aade4f4673656c543f4ccedc6`; kích thước 167625534 byte.
- Phát hành `beta`: chưa kiểm thử trên xe, chưa xác minh danh sách patch thực tế hoặc khả năng tự sáng/tối theo xe; không kế thừa xác nhận autotheme của bản cũ.
- `requires`: app.revanced.android.gms (chỉ cảnh báo, không chặn cài).
- minSdk 26, đáp ứng API 28 của IHU689G.
- Thay bản 21.16.256 autotheme (vc 1561068413), nhập vào hub 2026-11-11. Bản cũ được bỏ khỏi catalog để không được chọn thay cho bản 20.14.43 có versionCode thấp hơn; asset cũ trên GitHub Releases được giữ nguyên.
- Không thể cập nhật đè từ bản 21.16.256 vì versionCode giảm; cần gỡ bản cũ trước khi cài, dữ liệu ứng dụng có thể bị mất.
- Rollback: gỡ cài đặt thường; nếu cần quay lại bản autotheme cũ, cài APK `app.revanced.android.youtube-1561068413.apk` từ release `hub-2026.11.11`.
