# Omni-TikTok-Scraper

CLI + Web UI Python de lay danh sach video tu kenh TikTok, xuat metadata `JSON`/`CSV`, va tai video ve thu muc theo username.

## Cai dat

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## CLI

```powershell
omni-tiktok-scraper khaby.lame --limit 50
omni-tiktok-scraper tiktokuser:MS4w... --limit 50
```

Chi lay metadata:

```powershell
omni-tiktok-scraper khaby.lame --limit 100 --no-download
```

## Web UI

```powershell
omni-tiktok-web --host 127.0.0.1 --port 7860
```

Mo `http://127.0.0.1:7860`, nhap username/link hoac `tiktokuser:<channel_id/secUid>`, chon limit, output, cookie/proxy, roi bam `Bat dau tai`.

Hoac double-click `run-web.bat`.

O `Paste cookie` nhan 3 dang:

- JSON tu `omni-chrome-cookies`.
- Noi dung Netscape `cookies.txt`.
- Header `Cookie: a=b; c=d`.

Cookie paste duoc ghi thanh file tam va xoa sau khi job ket thuc.

Form Web UI tu luu vao `localStorage` cua trinh duyet, gom ca cookie paste neu ban da nhap.

Nut `Dung job` se dung process tai video dang chay. Bam `Ctrl+C` trong cua so server cung kill job con truoc khi thoat.

Thanh progress hien video dang tai, phan tram, toc do va ETA khi `yt-dlp` tra ve du lieu tien trinh. UI poll moi 1 giay.

Tu dong resolve profile `@username` sang `tiktokuser:<secUid>` khi co the de ne loi secondary user ID.

Neu o `So video` bi trong do data cu, backend tu dung `50` de tranh quet ca kenh.

## Tuy chon chinh

- `--limit 100`: gioi han so video. Bo qua de lay tat ca video extractor tra ve.
- `--no-download`: chi xuat metadata, khong tai video.
- `--video-only`: tai video voi metadata toi thieu, giam loi khi quet kenh lon.
- File `.mp4` da co se duoc skip, khong tai lai.
- `--output downloads`: thu muc output.
- `--format json|csv|both`: dinh dang metadata.
- `--cookies cookies.txt`: dung cookie Netscape tu trinh duyet/exporter.
- `--proxy http://user:pass@host:port`: dung proxy cho metadata va download.
- `--delay-min 1 --delay-max 4`: delay ngau nhien giua tung video download.
- `--retries 3`: so lan thu lai moi video.

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

## Ghi chu

- Video khong watermark phu thuoc URL/format TikTok ma `yt-dlp` trich xuat duoc tai thoi diem chay.
- TikTok hay doi API/chong bot. Neu bi chan, dung `--cookies`, tang delay, hoac dung `--proxy`.
- `curl_cffi` bat buoc de `yt-dlp` impersonate Chrome khi lay profile TikTok.
- Khong tu dong bypass CAPTCHA hoac co che bao ve dang nhap.
