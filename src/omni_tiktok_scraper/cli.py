from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import random
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.networking.impersonate import ImpersonateTarget


@dataclass
class VideoMetadata:
    index: int
    id: str
    video_url: str
    title: str
    caption: str
    upload_date: str | None
    duration: float | None
    views: int | None
    likes: int | None
    comments: int | None
    shares: int | None
    hashtags: list[str]
    music_info: dict[str, Any]
    author_info: dict[str, Any]
    downloaded_file: str | None = None
    error: str | None = None


def channel_url(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("username/link trống")
    if value.startswith(("http://", "https://", "tiktokuser:")):
        return value
    return f"https://www.tiktok.com/@{value.lstrip('@')}"


def channel_name(value: str) -> str:
    if value.startswith("tiktokuser:"):
        return clean_name(value.split(":", 1)[1][:32], "tiktokuser")
    match = re.search(r"tiktok\.com/@([^/?#]+)", value)
    if match:
        return clean_name(match.group(1))
    return clean_name(value.strip().lstrip("@"))


def clean_name(value: str, fallback: str = "untitled") -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|\r\n\t]+", " ", value).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return (cleaned[:120].rstrip(" .") or fallback)


def hashtags(info: dict[str, Any]) -> list[str]:
    tags = info.get("tags") or []
    if tags:
        return sorted({str(tag).lstrip("#") for tag in tags if str(tag).strip()})
    text = info.get("description") or info.get("title") or ""
    return sorted({tag for tag in re.findall(r"#([\w\u0080-\uffff]+)", text)})


def base_ydl_options(args: argparse.Namespace) -> dict[str, Any]:
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "extract_flat": False,
        "retries": args.retries,
        "fragment_retries": args.retries,
        "extractor_retries": args.retries,
        "noprogress": True,
    }
    if importlib.util.find_spec("curl_cffi"):
        options["impersonate"] = ImpersonateTarget(client="chrome")
    if args.cookies:
        options["cookiefile"] = args.cookies
    if args.proxy:
        options["proxy"] = args.proxy
    return options


def resolve_tiktokuser_url(url: str, args: argparse.Namespace) -> str:
    if url.startswith("tiktokuser:") or "tiktok.com/@" not in url:
        return url
    options = base_ydl_options(args) | {"extract_flat": True, "playlistend": 1}
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
    entries = info.get("entries") if isinstance(info, dict) else None
    sec_uid = info.get("id") if isinstance(info, dict) else None
    if entries:
        sec_uid = entries[0].get("channel_id") or sec_uid
    if isinstance(sec_uid, str) and sec_uid.startswith("MS4w"):
        print(f"Resolved profile to tiktokuser:{sec_uid}", flush=True)
        return f"tiktokuser:{sec_uid}"
    return url


def extract_entries(url: str, args: argparse.Namespace) -> list[dict[str, Any]]:
    url = resolve_tiktokuser_url(url, args)
    options = base_ydl_options(args) | {"playlistend": args.limit or None}
    if getattr(args, "video_only", False):
        options["extract_flat"] = True
    last_error: Exception | None = None
    for attempt in range(1, args.retries + 1):
        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as exc:  # noqa: BLE001 - retry flaky TikTok profile extraction.
            last_error = exc
            info = None
        if info:
            entries = info.get("entries") if isinstance(info, dict) else None
            rows = [info] if entries is None else [entry for entry in entries if entry][: args.limit or None]
            if rows:
                if attempt > 1:
                    print(f"Metadata retry succeeded on attempt {attempt}")
                return rows
        if attempt < args.retries:
            print(f"Metadata retry {attempt + 1}/{args.retries}")
            sleep_between(args)
    if last_error:
        print(f"Metadata failed after {args.retries} retries: {last_error}", file=sys.stderr)
    return []


def entry_url(entry: dict[str, Any]) -> str:
    for key in ("webpage_url", "original_url", "url"):
        value = entry.get(key)
    if value.startswith(("http://", "https://", "tiktokuser:")):
            return value
    return ""


def normalize(entry: dict[str, Any], index: int) -> VideoMetadata:
    title = entry.get("title") or entry.get("description") or entry.get("id") or f"video-{index:03d}"
    uploader = entry.get("uploader") or entry.get("channel") or entry.get("creator")
    music = {
        "track": entry.get("track"),
        "artist": entry.get("artist"),
        "album": entry.get("album"),
    }
    author = {
        "id": entry.get("uploader_id") or entry.get("channel_id"),
        "username": uploader,
        "url": entry.get("uploader_url") or entry.get("channel_url"),
    }
    return VideoMetadata(
        index=index,
        id=str(entry.get("id") or index),
        video_url=entry_url(entry),
        title=str(title),
        caption=str(entry.get("description") or title),
        upload_date=entry.get("upload_date"),
        duration=entry.get("duration"),
        views=entry.get("view_count"),
        likes=entry.get("like_count"),
        comments=entry.get("comment_count"),
        shares=entry.get("repost_count") or entry.get("share_count"),
        hashtags=hashtags(entry),
        music_info={key: value for key, value in music.items() if value},
        author_info={key: value for key, value in author.items() if value},
    )


def write_json(path: Path, rows: list[VideoMetadata]) -> None:
    path.write_text(json.dumps([asdict(row) for row in rows], ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[VideoMetadata]) -> None:
    fields = list(asdict(rows[0]).keys()) if rows else list(VideoMetadata.__dataclass_fields__.keys())
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            data = asdict(row)
            data["hashtags"] = ",".join(row.hashtags)
            data["music_info"] = json.dumps(row.music_info, ensure_ascii=False)
            data["author_info"] = json.dumps(row.author_info, ensure_ascii=False)
            writer.writerow(data)


def sleep_between(args: argparse.Namespace) -> None:
    if args.delay_max <= 0:
        return
    time.sleep(random.uniform(max(0, args.delay_min), max(args.delay_min, args.delay_max)))


def existing_video_file(videos_dir: Path, index: int, title: str) -> Path | None:
    exact = videos_dir / f"{index:03d} - {title}.mp4"
    if exact.exists() and exact.stat().st_size > 0:
        return exact
    matches = sorted(videos_dir.glob(f"{index:03d} - *.mp4"))
    return next((path for path in matches if path.stat().st_size > 0), None)


def make_progress_hook(row: VideoMetadata, total: int):
    last_emit = 0.0
    last_percent = -1

    def hook(data: dict[str, Any]) -> None:
        nonlocal last_emit, last_percent
        status = data.get("status")
        if status == "downloading":
            downloaded = data.get("downloaded_bytes") or 0
            total_bytes = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            if not total_bytes:
                return
            percent = int(downloaded * 100 / total_bytes)
            now = time.monotonic()
            if percent < 100 and percent == last_percent and now - last_emit < 1:
                return
            if percent < 100 and now - last_emit < 1:
                return
            last_emit = now
            last_percent = percent
            speed = data.get("speed") or 0
            eta = data.get("eta")
            print(f"PROGRESS {row.index}/{total} {min(percent, 100)}% speed={int(speed) if speed else 0}B/s eta={eta if eta is not None else '?'}s", flush=True)
        elif status == "finished":
            print(f"PROGRESS {row.index}/{total} 100% merging", flush=True)

    return hook


def download_one(row: VideoMetadata, videos_dir: Path, args: argparse.Namespace, total: int = 1) -> VideoMetadata:
    title = clean_name(row.title, row.id)
    existing = existing_video_file(videos_dir, row.index, title)
    if existing:
        row.downloaded_file = str(existing)
        row.error = None
        print(f"Skipping existing {row.index}: {existing.name}")
        return row

    filename = f"{row.index:03d} - {title}.%(ext)s"
    options = base_ydl_options(args) | {
        "outtmpl": str(videos_dir / filename),
        "format": "bestvideo*+bestaudio/best",
        "merge_output_format": "mp4",
        "writethumbnail": False,
        "continuedl": True,
        "overwrites": False,
        "progress_hooks": [make_progress_hook(row, total)],
    }
    last_error: Exception | None = None
    for attempt in range(1, args.retries + 1):
        try:
            with YoutubeDL(options) as ydl:
                result = ydl.extract_info(row.video_url, download=True)
                filepath = ydl.prepare_filename(result) if result else None
            row.downloaded_file = str(Path(filepath).with_suffix(".mp4") if filepath else videos_dir / filename.replace("%(ext)s", "mp4"))
            row.error = None
            return row
        except Exception as exc:  # noqa: BLE001 - CLI logs failure per video and continues.
            last_error = exc
            if attempt < args.retries:
                sleep_between(args)
    row.error = str(last_error) if last_error else "download failed"
    return row


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape metadata và tải video TikTok theo kênh.")
    parser.add_argument("target", help="Username hoặc URL kênh/video TikTok")
    parser.add_argument("--limit", type=int, default=None, help="Số video cần lấy; bỏ qua để lấy tất cả")
    parser.add_argument("--output", default="downloads", help="Thư mục output")
    parser.add_argument("--format", choices=("json", "csv", "both"), default="both", help="Định dạng metadata")
    parser.add_argument("--no-download", action="store_true", help="Chỉ xuất metadata")
    parser.add_argument("--video-only", action="store_true", help="T?i video v?i metadata t?i thi?u")
    parser.add_argument("--cookies", help="File cookie Netscape")
    parser.add_argument("--proxy", help="Proxy, ví dụ http://user:pass@host:port")
    parser.add_argument("--delay-min", type=float, default=1.0, help="Delay tối thiểu giữa download")
    parser.add_argument("--delay-max", type=float, default=4.0, help="Delay tối đa giữa download")
    parser.add_argument("--retries", type=int, default=3, help="Số lần retry mỗi video")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit phải >= 1")
    if args.retries < 1:
        parser.error("--retries phải >= 1")
    if args.delay_min < 0 or args.delay_max < 0 or args.delay_min > args.delay_max:
        parser.error("delay phải >= 0 và --delay-min <= --delay-max")
    return args


def run(argv: list[str]) -> int:
    args = parse_args(argv)
    url = channel_url(args.target)
    name = channel_name(url)
    channel_dir = Path(args.output) / name
    videos_dir = channel_dir / "videos"
    channel_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)

    entries = extract_entries(url, args)
    rows = [normalize(entry, index) for index, entry in enumerate(entries, start=1)]
    if not rows:
        print("Kh?ng l?y ???c video n?o. Th? cookie m?i ho?c nh?p d?ng tiktokuser:<channel_id/secUid>.", file=sys.stderr)
        return 2

    if not args.no_download:
        for row in rows:
            sleep_between(args)
            print(f"Downloading {row.index}/{len(rows)}: {row.video_url}")
            download_one(row, videos_dir, args, len(rows))

    if args.format in {"json", "both"}:
        write_json(channel_dir / "metadata.json", rows)
    if args.format in {"csv", "both"}:
        write_csv(channel_dir / "metadata.csv", rows)

    failed = [row for row in rows if row.error]
    if failed:
        write_json(channel_dir / "failed.json", failed)
        print(f"Xong, {len(failed)} video lỗi. Xem {channel_dir / 'failed.json'}")
        return 1

    print(f"Xong. Output: {channel_dir}")
    return 0


def main() -> None:
    configure_stdio()
    raise SystemExit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
