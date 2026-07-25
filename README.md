# Omni-TikTok-Scraper

CLI Python để lấy danh sách video từ kênh TikTok, xuất metadata `JSON`/`CSV`, và tải video về thư mục theo username.

## Cài đặt

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## Dùng nhanh

```powershell
omni-tiktok-scraper khaby.lame --limit 50
```

Hoặc:

```powershell
python -m omni_tiktok_scraper https://www.tiktok.com/@khaby.lame --limit 100 --format csv
```

## Tùy chọn chính

- `--limit 100`: giới hạn số video. Bỏ qua để lấy tất cả video extractor trả về.
- `--no-download`: chỉ xuất metadata, không tải video.
- `--output downloads`: thư mục output.
- `--format json|csv|both`: định dạng metadata.
- `--cookies cookies.txt`: dùng cookie Netscape từ trình duyệt/exporter.
- `--proxy http://user:pass@host:port`: dùng proxy cho metadata và download.
- `--delay-min 1 --delay-max 4`: delay ngẫu nhiên giữa từng video download.
- `--retries 3`: số lần thử lại mỗi video.

## Output

```text
downloads/
  khaby.lame/
    metadata.json
    metadata.csv
    failed.json
    videos/
      001 - caption.mp4
```

## Ghi chú

- Video không watermark phụ thuộc URL/format TikTok mà `yt-dlp` trích xuất được tại thời điểm chạy.
- TikTok hay đổi API/chống bot. Nếu bị chặn, dùng `--cookies`, tăng delay, hoặc dùng `--proxy`.
- Không tự động bypass CAPTCHA hoặc cơ chế bảo vệ đăng nhập.
