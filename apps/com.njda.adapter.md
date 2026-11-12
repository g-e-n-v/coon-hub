# com.njda.adapter — NJDA Connection Adapter

- Nguồn: pull từ xe. vc 20260227, versionName 1.5.0.260227064414, compile SDK 34.
- **Platform-signed** (AOSP testkey `b3998086d056cffa`) — thành phần projection hệ thống: chuyển hình/âm thanh điện thoại lên màn hình xe, xin quyền car (cluster, climate, audio volume), INTERACT_ACROSS_USERS, mic.
- **3 biến thể cùng versionCode** (khác digest, chỉ cài được 1):
  | Biến thể | sha256 |
  | --- | --- |
  | wireless-mic (canonical trong catalog) | `58731411353d70a196a07e74e48af7f7b22bfdc423b5f464f87e65bfde48f391` |
  | wireless | `3f5eb907ba271bbffbeaf8990c4d40d73857388696a5e3f186b8d3167bfd61ae` |
  | mic | `83edff4a3708f0f3a10f9c3efab96e0d7ce1e913979195e11b5734abb3267d14` |
  Nếu xe nào dùng biến thể khác, hãy promote đè factory asset tương ứng — KHÔNG biến chúng thành 3 release (trùng versionCode, validate chặn).
- Chưa có bản vá (releases rỗng) — chỉ đăng ký factory base để Coon detect trạng thái + khôi phục worst-case.
- Rollback: patch sau này phải versionCode > 20260227 và encode ngày `YYYYMMDDnn`; rollback qua uninstall update về bản /system.
