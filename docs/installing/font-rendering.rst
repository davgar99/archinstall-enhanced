Font rendering defaults
=======================

Desktop installations configure a conservative system-wide Fontconfig baseline intended to keep text crisp and readable without forcing a particular font family.

The baseline enables anti-aliasing and hinting, uses slight hinting to preserve glyph shape, and selects Fontconfig's default LCD filter when subpixel rendering is active. It also enables Arch's ``70-no-bitmaps-except-emoji.conf`` preset so scalable outlines are preferred over poor bitmap fallbacks while bitmap emoji remain available.

These settings are deliberately display-agnostic. Archinstall Enhanced does **not** force ``rgba=rgb`` because RGB, BGR, vertical subpixel layouts, rotated displays, and non-standard OLED layouts need different treatment. Desktop environments and users remain free to choose the correct subpixel geometry for the actual display.

The installer also deliberately avoids several older or more aggressive tweaks:

* no font-family aliases or additional font packages are installed by this rendering baseline;
* no ``.Xresources`` file is written into user home directories;
* no ``FREETYPE_PROPERTIES=truetype:interpreter-version=40`` override is added because that interpreter is already the current Arch/FreeType default;
* FreeType stem darkening is not forced globally because it can make glyphs heavy or fuzzy when the rendering stack is not using the matching gamma-correct pipeline;
* no unconditional ``fc-cache -fv`` rebuild is run because Fontconfig normally maintains its cache as fonts change.

The generated rendering file is ``/etc/fonts/conf.d/45-archinstall-enhanced-rendering.conf``. Its ordering leaves the normal Fontconfig local configuration path available for administrator overrides. Users can also apply desktop- or account-specific Fontconfig settings later.
