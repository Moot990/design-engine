from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps, features

from .common import EngineError


def font_path(arabic=False):
    names = ["NotoSansArabic-Regular.ttf"] if arabic else ["NotoSans-Regular.ttf", "DejaVuSans.ttf"]
    for base in (Path("/usr/share/fonts/truetype"), Path("/usr/share/fonts/opentype")):
        for name in names:
            found = next(base.rglob(name), None) if base.exists() else None
            if found:
                return str(found)
    if os.name == "nt":
        directory = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Fonts"
        for name in ("arial.ttf", "segoeui.ttf"):
            if (directory / name).is_file():
                return str(directory / name)
    raise EngineError("Required fonts unavailable; use the GitHub Actions runner")


@lru_cache(maxsize=2)
def media_executable(name):
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt":
        home = Path(os.environ.get("FREEVIDEO_HOME", str(Path.home() / "FreeVideo/FreeVideo-engine")))
        for path in (home / "tools").rglob(name + ".exe"):
            return str(path)
    raise EngineError(name + " unavailable; no software was installed automatically")


def wrap_pixels(draw, text, font, width, **kwargs):
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if draw.textlength(trial, font=font, **kwargs) > width and line:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines


def caption_frame(image_path, title, lesson, language, destination, variant=0, *, transparent=False):
    fallback_arabic = language == "ar" and not features.check("raqm")
    if fallback_arabic:
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
        except ImportError:
            raise EngineError("Arabic rendering needs RAQM or the small local-video shaping dependencies") from None
    def display(line):
        return get_display(arabic_reshaper.reshape(line)) if fallback_arabic else line
    if transparent:
        image = Image.new("RGBA", (720, 1280), (0, 0, 0, 0))
    else:
        with Image.open(image_path) as source:
            image = ImageOps.fit(source.convert("RGB"), (720, 1280), method=Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image)
    rtl = {"direction": "rtl"} if language == "ar" and not fallback_arabic else {}
    font = ImageFont.truetype(font_path(language == "ar"), 34)
    small = ImageFont.truetype(font_path(language == "ar"), 26)
    lines = wrap_pixels(draw, title, font, 580, **rtl)
    lesson_lines = wrap_pixels(draw, lesson, small, 580, **rtl)
    if len(lines) > 3 or len(lesson_lines) > 4:
        raise EngineError("Caption too long for the video safe area")
    top = 180 if variant % 2 == 0 else 215
    draw.rounded_rectangle((42, top - 25, 668, top + 45 * len(lines) + 20), radius=16, fill=(25, 31, 31))
    for n, line in enumerate(lines):
        draw.text((640 if language == "ar" else 66, top + n * 45), display(line), font=font, fill="#F8F3E8", anchor="ra" if language == "ar" else "la", **rtl)
    lower = 865
    draw.rounded_rectangle((42, lower - 25, 668, lower + 38 * len(lesson_lines) + 20), radius=16, fill=(25, 31, 31))
    for n, line in enumerate(lesson_lines):
        draw.text((640 if language == "ar" else 66, lower + n * 38), display(line), font=small, fill="#F8F3E8", anchor="ra" if language == "ar" else "la", **rtl)
    draw.text((66, 1080), "AI DESIGN CONCEPT", font=ImageFont.truetype(font_path(), 21), fill="white", stroke_width=1, stroke_fill="black")
    image.save(destination)


def run_media(command):
    command = [media_executable(command[0]), *command[1:]]
    try:
        result = subprocess.run(command, capture_output=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        raise EngineError("Media tool missing or timed out; check cloud runner setup") from None
    if result.returncode:
        # These processes handle only local media; still avoid including arbitrary metadata in logs.
        raise EngineError("Media processing failed; check file validity, fonts and ffmpeg availability")


def probe(path):
    result = subprocess.run([media_executable("ffprobe"), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, timeout=30)
    if result.returncode:
        raise EngineError("ffprobe could not validate the media")
    return json.loads(result.stdout)


async def _voice(text, voice, destination):
    import edge_tts

    for attempt in range(3):
        try:
            await asyncio.wait_for(edge_tts.Communicate(text, voice, rate="+0%").save(str(destination)), timeout=70)
            return
        except Exception:
            if attempt == 2:
                raise EngineError("Edge TTS unavailable; captions-only fallback used") from None
            await asyncio.sleep(2 ** (attempt + 1))


def render_short(images, texts, settings, language, directory, *, fixture=False, variant=0, publishing=False):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if not 4 <= len(images) <= 6:
        raise EngineError("A Short requires 4 to 6 accepted images")
    narration = texts["script"]
    warnings = []
    audio = directory / "narration.mp3"
    has_audio = False
    if not fixture:
        voices = settings["voices"][language]
        try:
            asyncio.run(_voice(narration, voices[variant % len(voices)], audio))
            duration = float(probe(audio)["format"]["duration"])
            if duration > settings["short_seconds"] - .5:
                raise EngineError("Narration was too long; captions-only fallback used")
            has_audio = True
        except EngineError as error:
            warnings.append(str(error))
    from .freevideo import animate_selected
    ai_clips, ai_warnings = ({}, []) if fixture else animate_selected(images, settings, directory / "freevideo", publishing=publishing)
    warnings.extend(ai_warnings)
    segments = []
    frames_per_image = round(settings["short_seconds"] * 24 / len(images))
    for n, (image, caption) in enumerate(zip(images, texts["captions"])):
        frame, segment = directory / f"frame-{n}.png", directory / f"segment-{n}.mp4"
        caption_frame(image, texts["hook"], caption, language, frame, variant, transparent=n in ai_clips)
        if n in ai_clips:
            # Discard all model-generated sound. Narration is exclusively edge-tts.
            seconds = frames_per_image / 24
            filters = f"[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,fps=24,trim=duration=5,tpad=stop_mode=clone:stop_duration={seconds},trim=duration={seconds}[v];[v][1:v]overlay=0:0:shortest=1,format=yuv420p[out]"
            try:
                run_media(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(ai_clips[n]), "-loop", "1", "-i", str(frame), "-filter_complex", filters, "-map", "[out]", "-an", "-frames:v", str(frames_per_image), "-c:v", "libx264", "-preset", "veryfast", "-b:v", "1000k", "-maxrate", "1200k", "-bufsize", "2000k", "-threads", "2", str(segment)])
                segments.append(segment)
                continue
            except EngineError:
                warnings.append("AI clip assembly failed; this scene uses the ffmpeg still-image fallback")
                caption_frame(image, texts["hook"], caption, language, frame, variant)
        zoom = "min(zoom+0.0006,1.07)" if (n + variant) % 2 == 0 else "if(eq(on,0),1.07,max(1.0,zoom-0.0006))"
        run_media(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(frame), "-vf", f"scale=1440:2560,zoompan=z='{zoom}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={frames_per_image}:s=720x1280:fps=24,format=yuv420p", "-frames:v", str(frames_per_image), "-c:v", "libx264", "-preset", "veryfast", "-b:v", "1000k", "-maxrate", "1200k", "-bufsize", "2000k", "-threads", "2", str(segment)])
        segments.append(segment)
    concat = directory / "concat.txt"
    concat.write_text("".join(f"file '{p.name}'\n" for p in segments), encoding="utf-8")
    output = directory / "short.mp4"
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "1", "-i", str(concat)]
    if has_audio:
        command += ["-i", str(audio), "-af", "apad", "-c:a", "aac", "-b:a", "96k"]
    command += ["-c:v", "copy", "-t", str(settings["short_seconds"]), "-movflags", "+faststart", str(output)]
    run_media(command)
    info = probe(output)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    if (video["width"], video["height"]) != (720, 1280) or not 15 <= float(info["format"]["duration"]) <= 30.1:
        raise EngineError("Rendered Short failed portrait/duration validation")
    for path in segments + [concat]:
        path.unlink(missing_ok=True)
    return output, warnings
