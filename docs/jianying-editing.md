# Local editable drafts with JianYing

Optional editing stage: prepare an editable local timeline after source media is final, then verify it in the native editor. This does not replace the existing content, AI-video, audio and publication checks.

## Dependency and installation

Upstream: [luoluoluo22/jianying-editor-skill](https://github.com/luoluoluo22/jianying-editor-skill), skill name `jianying-editor`, VERSION `1.7.0`, reviewed commit `32c56928ded4f9e2c2b80e099dc7abb793d2c30b`. Main code is MIT; bundled pyJianYingDraft is Apache-2.0. This project records the dependency and original workflow notes; it does not redistribute upstream skill text, example media or private production material. See [dependency manifest](skills-manifest.json).

Install from the original source using your host's skill installer, pinned to the reviewed commit. Review platform-specific requirements before installing dependencies; the upstream requirements list includes Windows UI Automation. Set `JY_SKILL_ROOT` explicitly and keep business scripts outside the skill directory.

## Local workflow

1. Freeze source media and its time map. Copy an independent snapshot and verify SHA256 before and after copying.
2. Choose a unique new draft name and explicit writable draft root. Reject an existing destination. Enforce `allow_replace=False` at creation: the wrapper's `overwrite=False` alone does not prevent all recovery paths from recreating a draft.
3. Set canvas size from actual media. Use verified source/target ranges to create editable segments without unintentional gaps, overlap, speed changes or reordering. Spoken-line timestamps are narration anchors, not verified visual cut frames.
4. Stage media inside the new draft. Preserve a separate backup and a manifest with input hashes, stream durations, segment ranges, asset checks and validation status.
5. Open the new draft in JianYing, play boundaries and the ending, then export. Verify the exported file independently before publication.

## Portrait compatibility in the reviewed version

The default normalizer treats widths not divisible by 16 as needing conversion, then produces a fixed 1920×1080 output. This can incorrectly process valid 1080×1920 portrait sources. Review the path before calling `add_media_safe/add_clip`.

For the pinned version, staging the original file with `_stage_local_asset` and importing it via `_add_video_safe` can bypass this conversion; verify that staged video hashes match the source and canvas remains portrait. These are internal methods, so reassess after upgrading. If conversion is necessary, generate a separately verified portrait-preserving file rather than accepting silent landscape padding.

## Sound, export and evidence

Keep only one active copy of original sound. If remuxing original AAC to a separate audio track, mute video segments and verify compressed audio packet hashes. Record actual audio and video durations separately; an audio-only tail must not be presented as existing video frames. Baked-in subtitles remain pixels unless separately reconstructed and checked.

The reviewed automatic MP4 exporter supports Windows UI Automation. On macOS, draft generation and native GUI export are separate steps; a saved JSON file is not proof of successful import or playback. Verify export duration, resolution, boundaries, visible evidence, subtitles, audio synchronization and loudness/ASR against the final script. Previous source-file QC does not qualify a newly exported file.

Online TTS can read local application device identifiers and send them with text to a service; cloud asset operations also connect externally. They are optional capabilities, not required by this local workflow. Keep them disabled unless separately authorized, check asset rights, and retain TLS verification. Read [AI video workflow](ai-video-workflow.md) for generated shots and [operations](operations.md) for final delivery checks.
