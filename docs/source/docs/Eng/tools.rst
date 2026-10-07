Tools Page
----------

* Measure - click to measure, right-click to clear. What you measure goes
  straight to the clipboard.

    * Colour picker - the colour under the cursor, copied as #rrggbb,
      rgb(...), hsl(...) or a CSS custom property.
    * Pixel ruler - the distance between two points.
    * Protractor - the angle between three.

* Region capture - drag out an area; it lands on the clipboard, and Copy last
  puts it there again.

  Pin last puts that capture on top of everything as a small window you can drag,
  scroll to resize, and close with a double-click or Escape - a specification, a
  colour reference or an error message kept beside what you are working on.
* Screen text: Tools → Read text first uses local OCR: Windows.Media.Ocr on Windows, Vision on macOS, or an installed Tesseract executable with language data. Local extraction needs neither cloud consent nor ANTHROPIC_API_KEY; an empty successful result does not upload a screenshot. Translation and questions can send recognized text to Anthropic only with separate text consent and your key. Screenshot fallback after local failure needs its own capture consent and the key. The result shows the backend and errors; consent can be withdrawn there.
* Recording: select an area and choose the output GIF or AVI before capture starts. Cancelling does not start recording. Frames are written incrementally on a background thread with a queue limited to three frames and 64 MiB; a single oversized frame is rejected. A full queue drops captures and preserves elapsed playback timing. Frame-rate, duration and frame-count limits and the optional camera inset remain. Stop finalizes asynchronously; the final file replaces the destination atomically only after success. Cancellation and write errors clean up the temporary file and preserve an existing destination.
* Virtual camera - send an area, overlays and all, as a webcam that Zoom, Teams
  or Discord can pick as their video source. Needs the optional pyvirtualcam
  package and a virtual camera driver; without either, the button says so.
* Camera - show any video input, including capture cards, as a circle, rounded
  rectangle or rectangle, with an optional border and mirroring. It is shown
  locally only and nothing is recorded.
* Pin a window... - keep another application's window on top, and change how
  see-through it is. Windows only.
* Replicate a window... - a second, small window showing a chosen window live,
  while the original stays where it is. Useful for keeping an eye on a video or
  a build while you work in front of it. Drag the replica to move it,
  double-click to close it. Windows and macOS (optional macos extra and permission; native macOS unverified here).

  A replica can show just part of the window - the top or bottom half, one side,
  or the centre - so a chat column or a progress bar can be pinned on its own.
  The part is kept as a proportion, so resizing the original still shows the same
  piece of it.
* Window layout - save where your windows are and put them back later.

:doc:`runtime_interoperability`

Tools → Color palette collects consecutive picker clicks when Collect colors is enabled. Name and group swatches, edit exact hex values, search, copy and remove colors; recent samples remain reusable. Up to 512 swatches and 50 distinct recent colors are saved locally and survive restart. Names are unique within each group (case insensitive); duplicate names are rejected. CSS and JSON export preserve RGB values; CSS variable name collisions get numeric suffixes. Export writes atomically. The Commands palette can also open Color palette.

Tools → Record area offers GIF or silent AVI (Motion JPEG), 1–20 fps, Pause/Resume and Cancel. Status shows effective seconds, accepted frames and drops. Paused time is excluded from playback and duration limits, including stopping while paused. AVI supports up to one hour and 72,000 frames, with a 2 GiB output limit; GIF retains the 120-second/600-frame limits. Both use the three-frame/64 MiB background queue and atomic output. AVI retains one JPEG and writes its index to disk; dropped intervals repeat the last image to preserve timing. Encoding, size-limit or disk failures and cancellation preserve an existing target. No audio is recorded.
