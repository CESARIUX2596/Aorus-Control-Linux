# Laptop controls

Lumen 1.2 adds a local **Laptop controls** page beside the keyboard studio.
It reads Linux hwmon temperatures, CPU usage, NVIDIA GPU temperature/load/power,
fan RPM when available, and battery percentage/status. Readings refresh every
five seconds and remain on the machine.

Temperature readings are shown without a fixed count limit. CPU package
temperature is separate from the numerically ordered physical core sensors;
other device sensors follow. The reference CPU exposes eight core temperatures
(Core 0–7) for its eight physical cores and sixteen logical CPUs.

The page also offers power-profile selection through `powerprofilesctl`, Wi-Fi
through NetworkManager, Bluetooth through BlueZ (with `rfkill` fallback), and
volume through PipeWire `wpctl`. Each control appears only when its local tool
and system interface are detected. The commands use fixed arguments; browser input
cannot provide shell text or filesystem paths.

The built-in shortcut reference follows the [AORUS 15P manual](https://download.gigabyte.com/FileList/Manual/AORUS15PVD_manual_v1_all.pdf):
`Fn+Esc` requests maximum fan speed; `Fn+F1` sleeps; `Fn+F2` toggles wireless;
`Fn+F3/F4` changes brightness; `Fn+F5/F6` controls display output; `Fn+F7` to
`Fn+F9` controls mute and volume; `Fn+F10/F11` controls touchpad and airplane
mode; and `Fn+Space` toggles keyboard lighting.

## Optional Gigabyte fan and charging controls

Fan modes and battery charge limits require the separate community
[`gigabyte-laptop-wmi` kernel driver](https://github.com/tangalbert919/gigabyte-laptop-wmi).
Its documentation marks the driver experimental and exposes controls through
`/sys/devices/platform/aorus_laptop`. Lumen does not download, build, or load
that kernel module. It detects the interface and shows fan mode buttons or
60/80/100% charging-limit presets only when the matching sysfs nodes exist.

The dashboard shows Normal, Silent, Gaming, and Auto maximum modes, plus fixed
fan-output presets at 25%, 50%, 75%, and 100%. The percentage is converted to
the driver's 0–255 setting; actual RPM depends on laptop firmware. Charge
presets are Default, 60%, 80%, and 100%. The root helper accepts only these
fixed values. It never accepts an arbitrary curve, path, or command. The
laptop's firmware `Fn+Esc` shortcut remains available for its maximum fan mode.

## Current-machine availability

The reference host exposes Intel CPU temperatures, NVIDIA GPU telemetry,
battery state, NetworkManager, `rfkill`, PipeWire, and the Gigabyte WMI fan
driver. After installing the hash-verified Fedora 43 driver package for kernel
7.2.15, Lumen read **CPU fan 1,486 RPM** and **GPU fan 1,643 RPM**. The driver
reported fan mode Normal. Lumen does not change the current fan mode or charge
limit on startup; the user chooses a control. Power-profile switching remains
hidden because `powerprofilesctl` is not installed.

The RPM package is a third-party GPL driver, not Gigabyte's software. The
published package hashes were checked before installation. The driver
maintainer describes it as experimental; fan-mode and fixed-output changes
remain firmware/BIOS dependent and were not changed as part of telemetry setup.
