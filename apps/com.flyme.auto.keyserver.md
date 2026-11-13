# com.flyme.auto.keyserver — AutoKeyServer

- Trạng thái: **beta**, cần kiểm thử trên HU thật; chưa coi là ổn định.
- Factory: `coolray-lab/extracts/factory-apks/GeelyAutoKeyServer.apk`, versionCode `26020313`, giữ nguyên APK nguồn.
- Patched: `coolray-lab/projects/coon/keyserver-patch/GeelyAutoKeyServer-appcoon-2026111301.apk`, versionCode `2026111301`, zipalign và ký platform key của firmware.
- Chuyển tiếp GELLY/MODE qua ordered broadcast `app.coon.intent.action.HARD_KEY_EVENT`, package đích `app.coon`; Bridge chạy hành vi factory khi Coon không claim.
- Đã thu hồi release `2026111201` khỏi catalog và xóa asset lỗi: bản đó chỉ đọc `persist.sys.coon.mode`, không chuyển tiếp sự kiện tới Coon. Giữ nguyên APK factory phục vụ rollback.
- Đã kiểm tra mở khóa panel và broadcast mô phỏng trên HU; chưa nghiệm thu đầy đủ thao tác phím vật lý.
- Factory và beta được kiểm tra chữ ký platform; digest và kích thước nằm trong catalog.
- Sau cài hoặc gỡ cập nhật, khởi động lại `com.flyme.auto.keyserver/.service.AutoKeyService`.
- Rủi ro: cập nhật app hệ thống có thể làm gián đoạn xử lý phím và kill các tiến trình dùng UID hệ thống. Cần kiểm thử phím gốc, phím gán và lifecycle trên HU.
- Rollback: gỡ cập nhật để PMS dùng lại bản `/system`; APK factory trên Releases phục vụ khôi phục khi mất bản gốc.
