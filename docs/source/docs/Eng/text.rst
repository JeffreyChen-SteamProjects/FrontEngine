Text Page
---------

.. image:: ../image/text/text.png

* Start draw text on screen - show the text.
* Opacity - how see-through the text is.
* Font size, Font, Color - how it looks.
* Outline - draw a contrasting edge so it stays readable over anything.
* Choose text alignment - which corner or the centre.
* Marquee - scroll the text sideways, with its own speed.
* Text source - where the words come from.

    * Static text - exactly what is in the box.
    * Clock / Date - a strftime format.
    * Countdown - minutes, HH:MM, or a full date.
    * Stopwatch - counts up from the moment it starts.
    * System stats - fields such as {cpu} {ram} {disk} {down} {up}.
    * Weather - fields such as {temperature} {description} {humidity} {wind},
      for the city named in Weather city.

* Show on all screen / Show on all window bottom / Target monitor - as elsewhere.

Text → Local TXT / JSON / CSV displays a UTF-8 file with a selectable field and 1–3600 second refresh. JSON fields use /key/index paths (for example /build/tasks); CSV uses unique headers and displays the selected column as lines. An empty field displays the whole file. Reads run in a worker with one pending read per feed, a 1 MiB input limit and 65,536 output characters. Missing files/fields, invalid format, permissions and size limits have explicit states; corrected files recover automatically. Presets save the file/field/interval. Portable scenes copy the selected data file, so sharing a package shares that snapshot.
