Presenting Page
---------------

* Screen annotation - draw over whatever is on screen.

    * Pen, Highlighter, Eraser, with a colour and a width.
    * Undo removes the last stroke; Clear removes all of them.
    * While drawing is on, this layer takes the mouse. Everything else here
      passes clicks through.

* Cursor emphasis - Highlight puts a ring around the pointer, Click ripple
  shows where you clicked, Spotlight darkens everything but the pointer.
* Keystroke display - show the keys you press, and the mouse buttons you
  click, for recordings and demos. Choose where the panel sits and how big the
  text is; mouse clicks can be turned off on their own.
* Magnifier - a lens that follows the cursor, from 1.5x to 6x.
* Whiteboard - an endless canvas.
* Freeze screen - cover the chosen screen with a photograph of itself, so what is
  projected or shared stays put while you open something else. Press the button or
  the shortcut again to release it; any key, or a double-click on the frozen image,
  also releases it.

    * Drag with the middle button to pan, scroll to zoom.
    * Strokes are kept in canvas coordinates, so panning and zooming leaves
      them where they belong.
    * Save whiteboard writes an image of the area you actually drew on.

Presentation → Whiteboard now has independent editable pages, drawing/selection modes, Shift multi-selection, stroke movement and deletion, and twenty undo states across pages. Middle drag pans and wheel zooms; hit testing and movement stay in canvas coordinates. Each page retains its own view. Save/Open editable file uses versioned .fewhiteboard JSON with all vector strokes and views, allowing edits after reopening; save/read validation runs on one background worker and failures preserve the current board or existing file. Export this page PNG flattens only that page, excluding controls, selection and view transforms, with full pen margins. Bounds: 50 pages, 2000 strokes/page, 100000 total points, eight MiB JSON; PNG up to 8192 pixels/side and 16 megapixels. Closing/Escape cancels pending writes and ignores late read results.
