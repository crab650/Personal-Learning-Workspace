import io

from PIL import Image, ImageOps, UnidentifiedImageError


def compress_image_to_webp(
    upload,
    *,
    max_source_bytes,
    max_file_bytes,
    max_pixels=25_000_000,
):
    stream = upload.stream
    stream.seek(0, 2)
    source_size = stream.tell()
    stream.seek(0)
    if source_size > max_source_bytes:
        raise ValueError(f"原始圖片不可超過 {_format_size(max_source_bytes)}")

    try:
        source = Image.open(stream)
        source.seek(0)
        if source.width * source.height > max_pixels:
            raise ValueError("圖片像素不可超過 2500 萬")
        source = ImageOps.exif_transpose(source)
        source.load()
    except ValueError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("無法辨識圖片格式") from exc

    has_alpha = source.mode in {"RGBA", "LA"} or "transparency" in source.info
    source = source.convert("RGBA" if has_alpha else "RGB")
    for max_side in (1600, 1400, 1200, 1000, 800):
        candidate = source.copy()
        candidate.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        for quality in (72, 62, 52):
            output = io.BytesIO()
            candidate.save(output, format="WEBP", quality=quality, method=6)
            if output.tell() <= max_file_bytes:
                return output.getvalue(), candidate.width, candidate.height

    raise ValueError(f"圖片壓縮後仍超過 {_format_size(max_file_bytes)}")


def _format_size(size_bytes):
    if size_bytes % (1024 * 1024) == 0:
        return f"{size_bytes // (1024 * 1024)}MB"
    if size_bytes % 1024 == 0:
        return f"{size_bytes // 1024}KB"
    return f"{size_bytes} bytes"
