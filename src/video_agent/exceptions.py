class VideoAnalyzerError(Exception):
    """Base exception for video analyzer failures."""


class VideoFileNotFoundError(VideoAnalyzerError):
    """Raised when the local video file does not exist."""


class LargeVideoConfirmationRequired(VideoAnalyzerError):
    """Raised when a large video needs explicit user confirmation before analysis."""


class UnsupportedVideoSourceError(VideoAnalyzerError):
    """Raised when the given video source cannot be processed."""