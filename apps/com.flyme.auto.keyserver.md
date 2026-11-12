# com.flyme.auto.keyserver — AutoKeyServer

- Trạng thái: **beta**, cần kiểm thử trên HU thật; chưa coi là ổn định.
- Factory: `coolray-lab/extracts/factory-apks/GeelyAutoKeyServer.apk`, versionCode `26020313`, giữ nguyên APK nguồn.
- Patched: `coolray-lab/extracts/apks/GeelyAutoKeyServer-patched.apk`, bản vá phím vô lăng cho Coon.
- APK patched nguồn cũng có versionCode `26020313`; bản hub được rebuild bằng apktool 3.0.3, chỉ tăng versionCode thành `2026111201`, zipalign và ký lại bằng platform key của firmware. Không thay đổi logic bản vá.
- Factory và beta được kiểm tra chữ ký platform; digest và kích thước nằm trong catalog.
- Sau cài hoặc gỡ cập nhật, khởi động lại `com.flyme.auto.keyserver/.service.AutoKeyService`.
- Rủi ro: cập nhật app hệ thống có thể làm gián đoạn xử lý phím và kill các tiến trình dùng UID hệ thống. Cần kiểm thử phím gốc, phím gán và lifecycle trên HU.
- Rollback: gỡ cập nhật để PMS dùng lại bản `/system`; APK factory trên Releases phục vụ khôi phục khi mất bản gốc.
