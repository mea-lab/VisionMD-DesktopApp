# Automatic subject selection

Subject auto-processing uses YOLO11n pose tracking, retaining every tracked person
as a candidate. The suggestion ranks temporal coverage, average keypoint
confidence, median foreground size, and detection confidence. It is a general
visibility heuristic; task-specific motion is not available before task selection.
All tracked candidates remain available for review, including briefly visible people.

The API returns `candidates` and `suggestedSubjectId` alongside the existing
per-frame `boundingBoxes`. Subject flags agree with the suggestion. The UI selects
that person and shows a Suggested label. Exactly one candidate advances to task
selection after state is applied. Multiple candidates require user confirmation;
zero candidates do not advance. Users can change the selection. Manual JSON imports
preserve their subject choices and do not automatically navigate.

The existing model installers provision and verify `yolo11n-pose.pt`. Tracking ID
fragmentation can produce extra candidates; this keeps the confirmation screen
open rather than silently treating a multi-candidate video as a single subject.
