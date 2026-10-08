Image Page
----------

.. image:: ../image/image_page/image_page.png

* Choose Image - pick the image to show.
* Start Play Image - show it.
* Opacity - how see-through the image is.
* Fullscreen - stretch to the whole screen.
* Show on all screen - one copy per monitor.
* Show on all window bottom - place it beneath other windows.
* Slideshow - show every image in a folder in turn.

    * Choose folder - where the images are.
    * Interval - seconds between images.
    * Shuffle - random order.
    * Include subfolders - look inside nested folders too.

* Target monitor - which screen to use, or ask each time.
* Recent - images you showed before.
* Open reference board... - pick several pictures at once and spread them on one
  canvas over the desktop. Drag each picture to arrange it, drag the background to
  pan, scroll to zoom, Delete removes the selected one, Escape closes the board.
  Close boards closes them all, and the Control Center reaches them too.

Image → Compare images opens two references in one zoomable/pannable view. Switch between side by side, transparent overlay, a sliding wipe divider and absolute RGB difference. Align top-left or centers without scaling, or proportionally fit B inside A. Scroll zooms both images together; the slider controls B opacity or divider position. Transparent pixels and padding are compared on white; black difference pixels mean identical RGB. Only the first animated frame is used. Decoding/alignment/difference runs in a worker, with one pending request and only the latest selection applied; opacity/wipe redraws reuse pixmaps. Inputs are limited to 64 MiB per file, 8,192 pixels per dimension and 16,777,216 pixels per image/aligned canvas. Failed selection preserves the previous pair; closing clears images and ignores late results.
