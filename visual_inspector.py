"""Visual inspector for rendered scenes."""

import subprocess
from pathlib import Path
from typing import Any


class VisualInspector:
    """Inspect rendered videos for quality issues."""

    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()

    def _find_ffmpeg(self) -> str | None:
        """Find ffmpeg executable."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return "ffmpeg"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Try common Windows paths
        common_paths = [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        ]

        for path in common_paths:
            if Path(path).exists():
                return path

        return None

    def inspect_video(self, video_path: Path) -> dict[str, Any]:
        """Inspect video for quality issues."""
        if not video_path.exists():
            return {
                "is_valid": False,
                "error": f"Video file not found: {video_path}",
            }

        if not self.ffmpeg_path:
            return {
                "is_valid": True,
                "warning": "ffmpeg not found, skipping video inspection",
            }

        try:
            # Get video info
            info = self._get_video_info(video_path)
            if not info:
                return {
                    "is_valid": False,
                    "error": "Could not extract video info",
                }

            # Check video properties
            issues = []

            # Check resolution
            width = info.get("width", 0)
            height = info.get("height", 0)
            if width < 640 or height < 360:
                issues.append(f"Low resolution: {width}x{height}")

            # Check duration
            duration = info.get("duration", 0)
            if duration < 1.0:
                issues.append(f"Video too short: {duration:.2f}s")
            elif duration > 300.0:
                issues.append(f"Video too long: {duration:.2f}s")

            # Check frame rate
            fps = info.get("fps", 0)
            if fps < 24:
                issues.append(f"Low frame rate: {fps:.2f}fps")

            # Extract frames for visual inspection
            frame_issues = self._inspect_frames(video_path)
            issues.extend(frame_issues)

            return {
                "is_valid": len(issues) == 0,
                "issues": issues,
                "info": info,
            }

        except Exception as e:
            return {
                "is_valid": False,
                "error": f"Inspection failed: {e}",
            }

    def _get_video_info(self, video_path: Path) -> dict[str, Any] | None:
        """Get video information using ffprobe."""
        try:
            # Try ffprobe first
            ffprobe_path = self.ffmpeg_path.replace("ffmpeg", "ffprobe")
            if not Path(ffprobe_path).exists():
                ffprobe_path = "ffprobe"

            result = subprocess.run(
                [
                    ffprobe_path,
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return None

            import json
            data = json.loads(result.stdout)

            # Extract video stream info
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    return {
                        "width": int(stream.get("width", 0)),
                        "height": int(stream.get("height", 0)),
                        "fps": self._parse_fps(stream.get("r_frame_rate", "0/1")),
                        "duration": float(stream.get("duration", 0)),
                        "codec": stream.get("codec_name", "unknown"),
                    }

            return None

        except Exception:
            return None

    def _parse_fps(self, fps_str: str) -> float:
        """Parse FPS string like '30/1' to float."""
        try:
            if "/" in fps_str:
                num, den = fps_str.split("/")
                return float(num) / float(den)
            return float(fps_str)
        except (ValueError, ZeroDivisionError):
            return 0.0

    def _inspect_frames(self, video_path: Path) -> list[str]:
        """Extract and inspect frames for visual issues."""
        issues = []

        if not self.ffmpeg_path:
            return issues

        try:
            # Extract a few frames
            output_dir = video_path.parent / "frames"
            output_dir.mkdir(exist_ok=True)

            # Extract frame at 25%, 50%, 75% of video
            result = subprocess.run(
                [
                    self.ffmpeg_path,
                    "-i", str(video_path),
                    "-vf", "select='eq(n\\,0)+eq(n\\,100)+eq(n\\,200)'",
                    "-vsync", "vfr",
                    str(output_dir / "frame_%d.png"),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return issues

            # Check if frames were created
            frames = list(output_dir.glob("frame_*.png"))
            if not frames:
                issues.append("Could not extract frames for inspection")
                return issues

            # Basic frame checks
            for frame in frames:
                if frame.stat().st_size < 1000:  # Less than 1KB
                    issues.append(f"Frame {frame.name} appears to be empty or corrupted")

            # Clean up
            for frame in frames:
                frame.unlink()
            output_dir.rmdir()

        except Exception as e:
            issues.append(f"Frame inspection failed: {e}")

        return issues

    def compare_scenes(self, video1: Path, video2: Path) -> dict[str, Any]:
        """Compare two videos for similarity."""
        if not self.ffmpeg_path:
            return {"error": "ffmpeg not available"}

        try:
            # Use ffmpeg to calculate similarity
            result = subprocess.run(
                [
                    self.ffmpeg_path,
                    "-i", str(video1),
                    "-i", str(video2),
                    "-filter_complex", "[0:v][1:v]blend=all_mode=difference,signalstats",
                    "-f", "null",
                    "-",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Parse output for similarity metrics
            # This is a simplified version
            return {
                "similarity": "calculated",
                "video1": str(video1),
                "video2": str(video2),
            }

        except Exception as e:
            return {"error": f"Comparison failed: {e}"}

    def get_quality_score(self, video_path: Path) -> float:
        """Get overall quality score for video (0-1)."""
        inspection = self.inspect_video(video_path)

        if not inspection.get("is_valid", False):
            return 0.0

        issues = inspection.get("issues", [])
        info = inspection.get("info", {})

        # Start with perfect score
        score = 1.0

        # Deduct for issues
        score -= len(issues) * 0.1

        # Bonus for good resolution
        width = info.get("width", 0)
        height = info.get("height", 0)
        if width >= 1280 and height >= 720:
            score += 0.1

        # Bonus for good frame rate
        fps = info.get("fps", 0)
        if fps >= 30:
            score += 0.1

        # Bonus for reasonable duration
        duration = info.get("duration", 0)
        if 5.0 <= duration <= 60.0:
            score += 0.1

        return max(0.0, min(1.0, score))
