# Video Agent

## Overview

The `video_agent` module adds backend video analysis support to the Course Assistant platform.

It is designed to evaluate project/demo videos against rubric criteria using Gemini. The module supports full video analysis, transcription-only analysis, large-video confirmation handling, and direct video URL/S3 presigned URL inputs.

This module currently lives under:

```text
src/video_agent/
```

## Files Added

```text
src/video_agent/__init__.py
src/video_agent/models.py
src/video_agent/prompts.py
src/video_agent/exceptions.py
src/video_agent/video_analyzer.py
```

A local/manual test script has also been added under:

```text
src/tests/video_agent/test_video_analyzer.py
```

## Main Entry Point

The main function is:

```python
analyze_video(
    video_source,
    rubric_criteria,
    decision=...,
    analysis_mode=...
)
```

## Supported Video Sources

The analyzer currently supports:

1. Local video file paths
2. Direct downloadable video URLs
3. S3 presigned URLs
4. Best-effort Gemini URL analysis for non-direct public URLs

Direct downloadable URLs and S3 presigned URLs are downloaded to a temporary local file first, then uploaded to Gemini Files API.

## Supported Video Extensions

Allowed extensions:

```text
.mp4
.mov
.avi
.mkv
.webm
.mpeg
.mpg
.m4v
```

## Analysis Modes

### 1. Full Video Analysis

Full video analysis uploads the complete video file to Gemini Files API.

Gemini evaluates:

- Spoken audio
- Visual demonstrations
- Screen recordings
- Slides shown in the video
- UI walkthroughs
- Code demos
- Demo flow
- Clarity and completeness

This mode provides the best evaluation quality but may cost more for large videos.

### 2. Transcription-Only Analysis

Transcription-only mode extracts audio from the video using `ffmpeg`, uploads the WAV audio to Gemini, transcribes the spoken content, and grades based only on the transcript.

This mode is useful as a lower-cost fallback for large videos.

Limitations:

- Visual UI behavior is not evaluated.
- Slides shown on screen are not evaluated unless described in speech.
- Code walkthrough quality may not be fully evaluated unless explained verbally.
- Demo completeness may receive a lower score if visual evidence is missing.

## Large Video Handling

The module uses a configurable size threshold before analyzing large videos.

Setting:

```env
VIDEO_LARGE_FILE_THRESHOLD_MB=100
```

If a video is larger than the configured threshold and the caller uses:

```python
decision=LargeVideoDecision.REQUIRE_CONFIRMATION
```

the analyzer returns a confirmation response instead of immediately calling Gemini.

The frontend can then show the user two choices:

1. Proceed with full video analysis
2. Proceed with transcription-only analysis

The user’s selected option can then be passed back as:

```python
LargeVideoDecision.PROCEED_FULL_VIDEO
```

or:

```python
LargeVideoDecision.PROCEED_TRANSCRIPTION_ONLY
```

## Configuration

The module uses settings from:

```text
src/config/settings.py
```

Required setting:

```env
GEMINI_API_KEY=your_gemini_api_key
```

Video-related settings:

```env
VIDEO_ANALYSIS_MODEL=gemini-2.5-flash
VIDEO_TRANSCRIPTION_MODEL=gemini-2.5-flash
VIDEO_LARGE_FILE_THRESHOLD_MB=100
VIDEO_FILE_PROCESSING_TIMEOUT_SECONDS=300
VIDEO_FILE_POLL_INTERVAL_SECONDS=5
```

The implementation intentionally uses:

```python
settings.GEMINI_API_KEY
```

instead of:

```python
settings.gemini_api_key
```

This is because the existing repository already uses the uppercase `GEMINI_API_KEY` setting, and this avoids breaking teammate code.

## Dependencies

Python dependency:

```text
google-genai
```

This should be present in:

```text
requirements.txt
```

Runtime dependency for transcription-only mode:

```text
ffmpeg
```

`ffmpeg` is required only when using transcription-only analysis.

It should be installed in the runtime container that performs video analysis, especially the worker container.

Example Docker install:

```dockerfile
RUN apt-get update \
    && apt-get install -y ffmpeg \
    && rm -rf /var/lib/apt/lists/*
```

## Gemini File Processing

The module uploads videos/audio to Gemini Files API and waits until the uploaded file becomes active.

The polling logic uses:

```python
_file_state_name()
```

This helper normalizes Gemini file state values so the analyzer can handle different enum/string state formats more robustly.

Relevant settings:

```env
VIDEO_FILE_PROCESSING_TIMEOUT_SECONDS=300
VIDEO_FILE_POLL_INTERVAL_SECONDS=5
```

## Result Shape

A successful result returns a dictionary similar to:

```json
{
  "criteria_scores": [
    {
      "category": "Technical Implementation",
      "score": 18,
      "max_score": 20,
      "comment": "The demo explains the backend flow clearly.",
      "evidence": "The video shows API behavior and explains the data flow."
    }
  ],
  "video_summary": "The video demonstrates the project workflow and explains the main features.",
  "analysis_mode": "full_video",
  "total_score": 18,
  "max_total_score": 20,
  "warnings": [],
  "metadata": {}
}
```

A large video confirmation response returns a dictionary similar to:

```json
{
  "requires_confirmation": true,
  "file_size_bytes": 125000000,
  "file_size_mb": 119.21,
  "threshold_mb": 100,
  "message": "This video is larger than the configured threshold...",
  "options": [
    {
      "id": "proceed_full_video",
      "label": "Proceed with full video analysis",
      "description": "Best accuracy. Gemini evaluates visuals, screen recording, slides, demo flow, and audio."
    },
    {
      "id": "proceed_transcription_only",
      "label": "Proceed with transcription-only analysis",
      "description": "Lower-cost fallback. Extracts/transcribes audio and grades only spoken content."
    }
  ],
  "selected_analysis_mode": "full_video"
}
```

## Manual Test Script

A manual test script exists at:

```text
src/tests/video_agent/test_video_analyzer.py
```

This script can be used later to test:

1. Small local video full analysis
2. Large video confirmation response
3. Large video proceed full video
4. Large video proceed transcription-only
5. Direct downloadable video URL / S3 presigned URL

Example command:

```bash
python src/tests/video_agent/test_video_analyzer.py \
  --video-source test_assets/demo_small.mp4 \
  --decision require_confirmation \
  --threshold-mb 1
```

## Current Testing Status

The module has not yet been tested with a real Gemini video analysis call.

Testing is intentionally deferred because real Gemini video analysis may add usage cost.


## Cost Considerations

Gemini calls may cost money.

The most expensive mode is expected to be:

```text
proceed_full_video
```

because Gemini processes both visual and audio content.

The lower-cost fallback is:

```text
proceed_transcription_only
```

but it still uses Gemini for:

1. Audio transcription
2. Transcript-based grading

The large-video confirmation response should not call Gemini if the file size is above the threshold and the decision is still `require_confirmation`.

## Future Scope

### Frontend Integration

The frontend should support a large-video confirmation flow.

Suggested UX:

1. User uploads or selects a video.
2. Backend checks size.
3. If the file is large, backend returns `requires_confirmation: true`.
4. Frontend shows a warning message explaining that full video analysis may cost more.
5. Frontend shows two buttons:
   - Proceed with full video analysis
   - Proceed with transcription-only analysis
6. Frontend sends the selected decision back to the backend.
7. Backend runs the selected analysis mode.

The frontend can use the returned `options` array directly to render the choices.

### API Integration

A future API endpoint can wrap `analyze_video()`.

Possible request shape:

```json
{
  "video_source": "s3-presigned-url-or-local-path",
  "rubric_criteria": [
    {
      "category": "Technical Implementation",
      "max_score": 20,
      "description": "Evaluate the technical completeness of the project."
    }
  ],
  "decision": "require_confirmation",
  "analysis_mode": "full_video"
}
```

Possible response shape:

```json
{
  "requires_confirmation": true,
  "message": "This video is larger than the configured threshold...",
  "options": []
}
```

or:

```json
{
  "criteria_scores": [],
  "video_summary": "",
  "analysis_mode": "full_video",
  "total_score": 0,
  "max_total_score": 0,
  "warnings": [],
  "metadata": {}
}
```


### Storage and Metadata

The `selected_mode` value is intentionally kept for future use.

It can later be stored in the database for:

- Audit logs
- User-facing status
- Cost analysis
- Debugging
- Re-running jobs
- Displaying whether the final grade used full video or transcript-only mode


### Test Improvements

The current test script is manual and intended for local validation.

Future automated tests can mock Gemini and test:

- Rubric validation
- Local file validation
- Large file confirmation response
- Decision-to-mode mapping
- JSON extraction
- Result normalization
- Direct URL detection
- Missing API key behavior
- Unsupported file type behavior


Suggested future marker:

```bash
pytest -m gemini_integration
```

This would allow normal tests to run without paid Gemini calls.

## Notes

This module is currently backend-only.

Frontend can be added later.