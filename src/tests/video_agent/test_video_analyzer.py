import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


SAMPLE_RUBRIC_CRITERIA = [
    {
        "category": "Problem Understanding",
        "max_score": 10,
        "description": "Explains the problem being solved, target users, and motivation clearly.",
    },
    {
        "category": "Technical Implementation",
        "max_score": 20,
        "description": "Demonstrates the core technical implementation, architecture, APIs, models, or data flow.",
    },
    {
        "category": "Demo Completeness",
        "max_score": 20,
        "description": "Shows a working end-to-end demo with important features and realistic usage.",
    },
    {
        "category": "Clarity of Explanation",
        "max_score": 10,
        "description": "Presents the project clearly with understandable narration and logical flow.",
    },
]


def print_json(result: dict) -> None:
    print(json.dumps(result, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Manual tester for src.video_agent.video_analyzer")
    parser.add_argument(
        "--video-source",
        required=True,
        help="Local video path, direct downloadable video URL, or S3 presigned URL.",
    )
    parser.add_argument(
        "--decision",
        default="require_confirmation",
        choices=[
            "require_confirmation",
            "proceed_full_video",
            "proceed_transcription_only",
        ],
        help="Large video decision mode.",
    )
    parser.add_argument(
        "--threshold-mb",
        type=int,
        default=None,
        help="Override VIDEO_LARGE_FILE_THRESHOLD_MB before importing video_analyzer.",
    )
    parser.add_argument(
        "--analysis-mode",
        default=None,
        choices=["full_video", "transcription_only"],
        help="Optional explicit analysis_mode value.",
    )

    args = parser.parse_args()

    if args.threshold_mb is not None:
        os.environ["VIDEO_LARGE_FILE_THRESHOLD_MB"] = str(args.threshold_mb)

    # Import after env overrides because video_analyzer loads settings at import time.
    from src.video_agent.models import LargeVideoDecision, VideoAnalysisMode
    from src.video_agent.video_analyzer import analyze_video

    decision = LargeVideoDecision(args.decision)

    analysis_mode = None
    if args.analysis_mode:
        analysis_mode = VideoAnalysisMode(args.analysis_mode)

    video_source = args.video_source

    if not video_source.startswith(("http://", "https://")):
        path = Path(video_source)
        print(f"Local file exists: {path.exists()}")
        if path.exists():
            print(f"Local file size MB: {round(path.stat().st_size / (1024 * 1024), 2)}")

    print(f"Decision: {decision.value}")
    if analysis_mode:
        print(f"Analysis mode: {analysis_mode.value}")

    result = analyze_video(
        video_source=video_source,
        rubric_criteria=SAMPLE_RUBRIC_CRITERIA,
        decision=decision,
        analysis_mode=analysis_mode,
    )

    print_json(result)


if __name__ == "__main__":
    main()