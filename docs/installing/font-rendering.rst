Font rendering defaults
=======================

Desktop installations include ``fontconfig`` and rely on Arch Linux's packaged Fontconfig defaults for normal rendering behavior.

The current Arch ``fontconfig`` defaults already enable anti-aliasing and hinting, use ``hintslight``, and select the ``lcddefault`` LCD filter. Archinstall Enhanced deliberately does not generate another rendering configuration that repeats or overrides those settings.

The project's only additional font-rendering policy is to enable Fontconfig's packaged ``70-no-bitmaps-except-emoji.conf`` preset system-wide::

   /etc/fonts/conf.d/70-no-bitmaps-except-emoji.conf
       -> /usr/share/fontconfig/conf.avail/70-no-bitmaps-except-emoji.conf

This prefers scalable fonts over poor bitmap fallbacks while continuing to allow bitmap emoji.

The installer preserves an administrator-provided regular file at that path, repairs an incorrect symlink, and rejects unexpected filesystem objects rather than replacing them. Re-running the configuration is safe and leaves an already-correct symlink unchanged.

Archinstall Enhanced does not force subpixel geometry, ``rgba`` values, font-family aliases, ``.Xresources`` settings, FreeType interpreter overrides, stem darkening, or extra embedded-bitmap rules. Display-specific rendering choices remain under the control of the desktop environment, administrator, or user.

No font-cache rebuild is required merely to enable this Fontconfig selection rule.
