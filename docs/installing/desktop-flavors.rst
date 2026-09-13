Desktop installation flavors
============================

Archinstall Enhanced keeps the normal desktop-environment selection list. After a user selects a supported desktop, the installer asks how much of that desktop to install.

The common choices are:

* **Basic** — the smallest supported package set for users who want to assemble most optional applications and integrations themselves.
* **Standard (Recommended)** — a balanced desktop suitable for most users.
* **Complete** — a broader package set with additional applications or desktop integrations where upstream or Arch packaging guidance provides a clear definition.

The flavor prompt is shown only after the desktop itself is selected, so the desktop list remains uncluttered. If more than one desktop environment is selected, each supported desktop gets its own flavor prompt.

Supported desktops
------------------

KDE Plasma
~~~~~~~~~~

* **Basic:** ``plasma-desktop``.
* **Standard (Recommended):** ``plasma-meta``.
* **Complete:** ``plasma-meta`` plus a curated set of KDE-recommended file-management, thumbnailing, sharing, backup, device, image-format, OCR, accessibility, and desktop-integration packages based on KDE's distribution packaging recommendations and packages available in the Arch repositories.

Hardware-specific or mutually exclusive system services are intentionally left to their dedicated installer menus instead of being forced by the Complete desktop flavor.

GNOME
~~~~~

* **Basic:** the existing minimal GNOME shell/session/settings/file-manager package set.
* **Standard (Recommended):** the Arch ``gnome`` group plus ``gnome-tweaks``.
* **Complete:** the Standard set plus the Arch ``gnome-extra`` group.

Xfce
~~~~

* **Basic:** the Arch ``xfce4`` group.
* **Standard (Recommended):** ``xfce4`` plus volume control, GVFS integration, and archive support.
* **Complete:** the Standard set plus ``xfce4-goodies``.

MATE
~~~~

* **Basic:** the Arch ``mate`` group.
* **Standard (Recommended):** ``mate`` plus a terminal, archive manager, and document viewer.
* **Complete:** ``mate`` plus ``mate-extra``.

COSMIC
~~~~~~

* **Basic:** ``cosmic-session`` plus user-directory support.
* **Standard (Recommended):** the Arch ``cosmic`` group.
* **Complete:** the Standard set plus keyring, printer-settings, and GTK settings integration.

Deepin
~~~~~~

* **Basic:** the Arch ``deepin`` group.
* **Standard (Recommended):** the historical Archinstall Enhanced Deepin package set with terminal and editor.
* **Complete:** ``deepin`` plus ``deepin-extra``.

Saved configurations
--------------------

The selected flavor is stored in the desktop profile's custom settings. Older saved configurations that predate this feature keep their historical package behavior unless the user explicitly selects a new flavor. Existing GNOME and KDE Plasma flavor settings are also accepted so upgrades do not fail on older configuration files.
