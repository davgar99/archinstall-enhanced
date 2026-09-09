Windows dual boot
=================

Archinstall Enhanced can be used alongside an existing Windows installation, but dual-boot partitioning is destructive if the wrong partition is selected. Back up important data before changing the disk layout and keep the Windows recovery information available.

Before starting
---------------

* Save the recovery key if Windows device encryption or BitLocker is enabled. Suspend protection before changing partitions or EFI boot configuration, then resume it after both operating systems boot normally.
* Shrink the Windows volume from Windows Disk Management and leave the new space unallocated. Do not create a Linux filesystem from Windows.
* Disable Windows Fast Startup before sharing or modifying Windows filesystems from Linux. A fully hibernated Windows volume should not be mounted read-write from Linux.
* Boot the installation media in UEFI mode when Windows is installed in UEFI mode. Mixing legacy BIOS and UEFI installations makes boot management unnecessarily difficult.

Partitioning
------------

For an existing Windows installation, use manual partitioning and verify every selected partition before confirming installation.

* Do not format the Windows system, recovery, Microsoft reserved, or data partitions.
* Create the Linux root filesystem in the unallocated space created earlier. Add separate Linux partitions only when you actually need them.
* An existing EFI System Partition can normally be reused rather than creating a second one. Assign the intended mount point without formatting the partition and make sure it has enough free space for the selected boot setup.
* If you create a disk-backed swap partition for hibernation, Archinstall Enhanced can include that partition in LUKS encryption so hibernated memory is not stored in plaintext.

Review the final partition summary carefully. Device names can change between boots, so identify partitions by size, filesystem, purpose, and existing contents rather than relying only on names such as ``nvme0n1p1``.

Booting Windows and Linux
-------------------------

Keep the existing Windows Boot Manager EFI entry. The Linux bootloader and the firmware's own UEFI boot menu are separate ways to select an operating system, so the firmware boot menu remains a useful fallback even when a bootloader does not automatically create a Windows menu entry.

After installation, verify that both operating systems boot before deleting installation media or changing firmware boot entries. If Windows no longer appears first in firmware, adjust the firmware boot order rather than recreating or formatting its EFI partition.

Clock behavior
--------------

When a Windows Boot Manager EFI entry is detected, Archinstall Enhanced defaults away from storing the hardware clock as UTC. This avoids the common situation where Windows and Linux display different local times after switching between them. The setting remains user-configurable when a different clock policy is required.

Recovery checklist
------------------

If one operating system does not appear after installation:

#. Check the firmware UEFI boot menu for both Windows Boot Manager and the Linux boot entry.
#. Confirm that the existing EFI System Partition was not formatted.
#. Confirm that Windows device encryption or BitLocker has the expected recovery state.
#. Boot the installation media and inspect the partition table before attempting any repair.

Do not recreate filesystems or EFI partitions merely because a boot menu entry is missing; boot-entry problems and filesystem problems are different failures.
