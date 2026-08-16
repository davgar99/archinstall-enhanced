# Archinstall Enhanced

<img src="https://github.com/archlinux/archinstall/raw/master/docs/logo.png" alt="Archinstall logo" width="200"/>

An enhanced fork of [Archinstall](https://github.com/archlinux/archinstall) focused on making Arch Linux desktop and gaming installations more complete out of the box.

This fork adds more gaming, performance, desktop, and system configuration options directly to the Archinstall guided installer. The goal is to make it easier to install a well-configured Arch Linux system without having to manually set up many of these features after the first boot.

Changes included in this fork are intended to be stable, properly implemented, and backed by official documentation, upstream behavior, or established community recommendations whenever possible. Experimental features are clearly identified and remain optional.

This project is not intended to throw random performance tweaks into Archinstall. Features are added because they provide a useful configuration option, solve a real problem, improve the installation experience, or make common desktop and gaming setups easier to configure.

> [!IMPORTANT]
> This is an independent fork of Archinstall. It is not the official Arch Linux installer.
>
> Installing the `archinstall` package from the Arch Linux repositories will install the official upstream version, not the changes included in this repository.

## Why this fork exists

Archinstall provides a very good base for installing Arch Linux, but it intentionally keeps the default installer fairly general.

For desktop and gaming systems, there are still a number of useful packages, services, and configuration options that users commonly set up manually after installation.

Archinstall Enhanced tries to bring more of that setup into the installer itself while keeping the familiar Archinstall workflow.

The main goals of the project are:

- provide useful desktop and gaming options during installation
- make commonly used system configuration easier to set up
- provide optional performance tuning without forcing it on the user
- keep experimental features clearly separated from stable features
- use documented and maintainable configuration methods
- preserve normal Arch Linux behavior whenever possible
- remain close enough to upstream Archinstall that upstream changes can still be incorporated cleanly

Most additional features are optional. Users can decide how much or how little they want the installer to configure.

## Main differences from upstream

### Gaming and performance

The guided installer includes a **Gaming** section with optional support for:

- sched-ext CPU schedulers
- `scx_loader`
- Gaming mode scheduler configuration
- NTSYNC through `ntsync-autoload`
- GameMode
- MangoHud
- Gamescope
- optional AMD and Intel hardware watchdog configuration for advanced users

Stable and experimental sched-ext schedulers are separated so users can tell which options are considered more mature.

Experimental features such as NTSYNC are also identified as experimental instead of being presented as normal system defaults.

Multilib is enabled automatically only when a selected feature requires a 32-bit package such as:

- `lib32-gamemode`
- `lib32-mangohud`

If none of the selected options require Multilib, the installer does not enable it unnecessarily.

### Zram

Swap-on-zram can be configured directly through the installer.

The fork also provides optional virtual memory tuning for users who want to adjust the system around zram.

These settings are not silently applied. The additional tuning can be enabled or disabled independently, and the selected configuration is saved along with the rest of the Archinstall configuration.

### Desktop configuration

Archinstall Enhanced can install and configure additional packages when the user selects features that need them.

Examples include:

- `rtkit` with PipeWire for real-time audio scheduling
- Avahi for network service discovery
- `nss-mdns` for `.local` hostname resolution
- network printer discovery
- print service configuration
- Bluetooth configuration
- power management options
- firewall configuration
- additional font packages

The installer does not automatically install every optional component.

If a feature is not selected, the packages and services associated with that feature are left out.

### Pacman configuration

Additional Pacman settings are exposed through the guided installer.

Current options include:

- Parallel Downloads without requiring `--advanced`
- Pacman color output
- `ILoveCandy`

These settings are also saved and restored through the normal Archinstall configuration system.

### Installer improvements

The fork includes several smaller improvements to the guided installation experience.

These include:

- combined timezone and automatic NTP configuration
- consistent `Setting: Value` configuration summaries
- consistent `Enabled` and `Disabled` status formatting
- configuration persistence for the additional menus introduced by the fork
- proper console font restoration when changing installer languages
- improved handling of HiDPI console font configurations
- better network printer and mDNS configuration handling

The goal of these changes is to make the installer easier to use without changing the overall Archinstall workflow.

## Stability and implementation

Archinstall Enhanced is meant to provide useful additions without sacrificing the reliability expected from an operating system installer.

Changes should be based on proper documentation and tested behavior instead of being added simply because a tweak is popular.

When applicable, implementation decisions are based on sources such as:

- Arch Linux documentation
- the Arch Wiki
- Linux kernel documentation
- upstream project documentation
- upstream Archinstall behavior
- established community recommendations
- testing and regression coverage

Features that are still considered experimental should remain optional and should be clearly identified as experimental.

The project also tries to avoid unnecessary defaults that could negatively affect compatibility, security, or system stability.

## Installation

The easiest way to use Archinstall Enhanced is from an official Arch Linux live ISO.

The Arch Linux live environment already runs as root, so `sudo` is not required.

```bash
pacman -Sy --needed git
git clone https://github.com/davgar99/archinstall-enhanced.git
cd archinstall-enhanced
python -m archinstall
```

You can also install the project into the live environment:

```bash
pip install --break-system-packages .
archinstall
```

### Updating an existing clone

```bash
git pull --ff-only
python -m archinstall
```

## Configuration files

Archinstall can save and load installer configuration using JSON files.

The additional settings introduced by this fork use the existing Archinstall configuration system instead of relying on separate configuration files.

Example configuration files are available here:

- [`examples/config-sample.json`](examples/config-sample.json)
- [`examples/creds-sample.json`](examples/creds-sample.json)

A saved configuration can be loaded with:

```bash
archinstall --config user_configuration.json --creds user_credentials.json
```

User credentials can also be encrypted using Archinstall's existing credentials encryption support.

## Staying close to upstream

This fork is based directly on the official Arch Linux Archinstall project.

One of the goals of the project is to stay reasonably close to upstream instead of turning the installer into a completely separate codebase.

Upstream changes can be reviewed and incorporated while keeping the additional functionality provided by this fork.

When an improvement makes sense for Archinstall in general, upstream implementation and discussion should be considered before creating a separate fork-specific solution.

## Testing

The repository keeps the upstream testing and linting infrastructure.

Useful development checks include:

```bash
pytest
ruff check .
ruff format --check .
mypy .
```

Installer changes should also be tested in an Arch Linux environment whenever practical.

Changes involving partitioning, bootloaders, filesystems, encryption, or other installation-critical behavior should be tested using a disposable virtual machine or test disk before being used on a real system.

Do not test experimental partitioning or installation changes against a disk containing important data.

## Upstream Archinstall

For general Archinstall documentation and information, use the official upstream resources:

- [Archinstall documentation](https://archinstall.archlinux.page/)
- [Archinstall GitHub repository](https://github.com/archlinux/archinstall)
- [Arch Linux Wiki](https://wiki.archlinux.org/)

Problems caused specifically by changes in Archinstall Enhanced should be reported to this repository rather than upstream Archinstall.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution guidelines included with the repository.

For changes specific to this fork, patches should stay focused and include a clear reason for the change.

When adding new performance, gaming, storage, security, or system configuration features, documentation supporting the implementation should be included whenever possible.

New features should avoid changing existing Archinstall behavior unless there is a good reason to do so.

## License

Archinstall is licensed under the GNU General Public License v3.0.

Archinstall Enhanced keeps the same license.

See [LICENSE](LICENSE) for details.
