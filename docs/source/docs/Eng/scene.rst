Scene Page
----------

.. image:: ../image/scene/scene.png

A scene holds several overlays at once and can be saved to a file.

* Add web to scene - address and opacity.
* Add video to scene - file, opacity, play rate, volume.
* Add image to scene - file and opacity.
* Add gif to scene - file, opacity, speed.
* Add sound to scene - file and volume.
* Add text to scene - text, opacity, font size, alignment.
* Start scene - show everything that was added.
* output scene file - save what you built.
* load scene file - bring a saved scene back.
* clear all script - start again.
* Show on all screen - one copy per monitor.

Scenes: the Scene page accepts old entry-mapping JSON, a versioned frontengine.scene envelope, and portable .fescene packages. Add a PUPPET entry with position, size, opacity, finite numeric parameters, optional motion, expression and script. Paths in JSON resolve relative to the scene file. A .fescene includes the referenced media, original .puppet and optional .petscript.json so it can move between machines. Import checks paths, symlinks, versions and extraction limits. A FrontEngine scene remains a scene package; .puppet remains one Imervue character.

:doc:`runtime_interoperability`
