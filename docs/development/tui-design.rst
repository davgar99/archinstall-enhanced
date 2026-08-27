Archinstall Enhanced TUI stability
==================================

The guided installer deliberately retains upstream Archinstall's presentation:
a blue title bar, black content background, white menu text, the standard blue
focused row, a vertical preview divider, and the stock footer. The product title
is ``Archinstall Enhanced``; an available-update notice may follow it.

Menus
-----

Grouped menus use ``MenuItemRole.SECTION`` for subtitles. Rendering adds exactly
one blank terminal row before every section subtitle, including the first one.
Informational rows use ``MenuItemRole.INFORMATION`` and do not receive section
spacing. Labels remain plain translated text; markup and status prefixes are
presentation metadata so filtering and focus lookup use the real label.

Selectable rows reserve a two-column status gutter. Warnings and blockers both
use the master's yellow ``!`` marker. Their preview messages and the final
Install guard state whether an issue is advisory or blocks installation. There
is no status legend, required-setting count, or semantic action palette.
The final Save configuration, Install, and Abort commands are indented beneath
an Actions subtitle so they read as one group without changing their labels.

Validation
----------

The main menu has one state provider for authentication, disk and kernel
requirements, bootloader layout, desktop-user requirements, and network
warnings. The same blocking issues drive the Install preview and final guard.
Network configuration remains a warning; missing required settings and invalid
layouts block installation.

Workers and activities
----------------------

Worker results distinguish success, cancellation, and failure. Failures retain
the original exception object. A successful callback may return ``None``.
Dismissed screens ignore late updates, reset and retry flows use loops, and the
global application reference plus console font and logging state are restored
during cleanup.

``Activity`` runs work on a background worker. Unknown-duration work shows a
spinner; measured stage work shows real step progress. Both show the current
detail and elapsed time using the existing blue/black/white styling and stock
footer. Activity content is not placed in a bordered panel. Operations are only
cancellable when their collaborators can stop safely; protected operations
explain that cancellation is unavailable.

Installation and network operations
-----------------------------------

Installation stages report real boundaries and keep filesystem, installer, log
synchronization, post-install actions, reboot, and chroot ordering explicit.
Silent mode performs the same core operation without starting a TUI. The result
records elapsed time, target mountpoint, and log path.

Wi-Fi scanning and connection polling have configurable timeouts and observe
cancellation. Commands use argument vectors and the selected interface,
network ID zero is valid, and WPA values are JSON-escaped before being written.
Failures provide a retry-oriented message without routing secrets into status
details.

Testing
-------

Pilot coverage must exercise 160×50, 100×30, and 80×24 terminals, including
the canonical title, initial and repeated section spacing, filtering, focus
recovery, preview updates, scrolling, long translations, and footer visibility.
Worker tests cover values and ``None``, exception identity, cancellation,
protected operations, cleanup, and ignored late updates. Polling tests use short
configured timeouts and verify recovery messages.
