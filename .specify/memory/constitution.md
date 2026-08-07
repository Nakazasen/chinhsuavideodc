<!--
Sync Impact Report:
- Version change: Template -> 1.0.0 (Initial ratification of project constitution)
- Modified principles: Ratified 5 core principles tailored to chinhsuavideodc project
- Added sections: Core Principles, Technology & Security Constraints, Development Workflow, Governance
- Removed sections: Template placeholders
- Deferred TODOs: None
-->

# chinhsuavideodc (Video Object Remover & Masker) Constitution

## Core Principles

### I. MVP Architecture & Layer Separation
Pure separation between core computer vision algorithms (`src/core/`), GUI components (`src/gui/`), and CLI interfaces (`src/cli/`). Core video processing and tracking logic MUST remain independent of UI presentation details.

### II. Dual Interface Parity (GUI & CLI)
All core capabilities—including object removal (inpaint), masking, blurring, cropping, time-range trimming, and ROI selection—MUST be fully operational and consistent across both the GUI (Tkinter) and CLI interfaces.

### III. Non-Destructive Data Safety
Input video files MUST be opened in read-only mode. All generated or edited video outputs MUST be stored as new files inside the designated `outputs/` directory. Overwriting or mutating raw input videos is strictly FORBIDDEN.

### IV. Real-Time Performance & Responsive Feedback
Frame processing, preview playback (30 FPS target), and tracking loops MUST provide realtime progress updates (percentage and frame metrics). UI responsiveness MUST be maintained during heavy rendering tasks using background worker threads or non-blocking loop iterations.

### V. Robust Computer Vision & Tracking Integrity
Object tracking algorithms (e.g., MIL Tracker) and image transformations MUST handle boundary padding, tracking failures, irregular ROI coordinates, and variable frame sizes gracefully without throwing unhandled exceptions or crashing the application.

## Technology & Security Constraints

- **Language & Libraries**: Python 3.8+ compatibility, OpenCV (`opencv-python`), Tkinter, Pillow, and NumPy.
- **Local Data Privacy**: All video processing operates 100% locally. No unauthorized network requests, external telemetry, or cloud data streaming.
- **Resource Management**: Video capture and writer instances (`cv2.VideoCapture`, `cv2.VideoWriter`) MUST be explicitly released upon task completion or cancellation.

## Development & Quality Workflow

- **Testing & Verification**: Every new processing mode, UI control, or CLI option MUST be verified against test video samples in `samples/`.
- **Documentation Hygiene**: Architecture diagrams (`docs/ARCHITECTURE.md`) and user instructions (`README.md`) MUST be updated alongside any structural changes.
- **Clean Code Standards**: Code additions MUST adhere to `clean-code` standards: modular, self-documenting, readable, and free of dead code.

## Governance

This Constitution supersedes all informal practices. Proposed changes to project architecture or core principles require a pull request update to this document, explicit version bump according to Semantic Versioning rules, and approval by project maintainers.

**Version**: 1.0.0 | **Ratified**: 2026-08-04 | **Last Amended**: 2026-08-04
