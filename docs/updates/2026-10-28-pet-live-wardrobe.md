# Live layered playback

Wardrobe Apply now publishes its prepared renderer through the active profile
session only after persistence succeeds. Desktop pets adopt the renderer on the
session change signal. Existing sprite playback remains the fallback when no
layered renderer is active. Clothing composition precedes existing mirroring,
scaling and audio transforms.

LayeredPlayback owns an active-time clock but no timer. Desktop update ticks
select the action and request repaint; action changes restart the shared frame
timeline. Hide pauses playback and suspends movement, chatter and reminder
timers. Show resumes them. Closing releases the widget's renderer reference.

Verification found a pre-existing destruction-order exception in companion menu
cleanup. Replacing a manual destroyed-signal disconnect with a menu-owned QObject
receiver lets Qt disconnect safely regardless of whether menu or session dies first.

49 wardrobe, live profile, drop, typing-settlement and layered-renderer tests
passed after that correction. Pyflakes passed for the modified implementation
modules. New pixel assertions verify actual desktop pixmap publication, animation
advancement, hidden-time pause and preservation of the displayed outfit on disk
failure. Timer assertions verify hide/show suspension and restoration. All tests
used Qt offscreen; no native desktop verification is implied.

The wardrobe dialog, installed asset catalog, restart-time reference resolution,
official layered animation assets and native acceptance remain pending. The
entire pet feature goal is still active.
