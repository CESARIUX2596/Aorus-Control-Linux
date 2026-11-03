# Keyboard protocol and compatibility

This project targets the **1044:7a3f** Gigabyte / Chu Yuen Fusion keyboard,
observed in an **AORUS 15P YD**, USB revision 1.30. It does not claim support
for every AORUS or Gigabyte laptop.

The transport selects the exact 31-byte HID report descriptor on USB interface
3: vendor usage page `ff01`, usage `01`, unnumbered 8-byte feature reports and
64-byte input/output reports. Interface 0 handles typing and is never detached.
At open time, the file descriptor's USB ID and report descriptor are checked
again. hidraw node numbering is discovered dynamically.

## Evidence

Protocol analysis used the official Windows Control Center **25.11.12.01** for
[AORUS 15P Intel 11th Gen](https://www.aorus.com/be/laptops/AORUS-15P--Intel-11th-Gen/support/driver),
inspected statically using REA 6.8.0. No proprietary binaries or decompiled
application source are included in this repository.

The investigated FusionKeyboard DLL SHA-256 is
`44a2384a56b350f77a77968c3b958f50a8cf0fe0dcd54145ca587f01e75bdf34`,
MVID `89826b79-45c2-4db0-a8d5-d5f583986956`. Method tokens below refer to this build only.

| Observation | Vendor method |
| --- | --- |
| Explicit `1044` / `7a3f` match and 9-byte Windows feature buffer | `FusionDevice.initKeyboard`, `0x0600014c` |
| Header field order, checksum, 65 ms delay | `FusionDevice.SetLightEffect`, `0x0600014e` |
| 512-byte custom upload, eight output reports, 100 ms pacing | `FusionDevice.SetPictureMatrix2Device`, `0x06000165` |
| RGB component order in each slot | `FusionDevice.modifySingleBtnColor`, `0x06000169` |
| Custom effect maps to slot `effect - 51` | `FusionController.setGamePicture`, `0x0600011e` |

The English key positions were checked against the vendor's 105-entry slot map.
Y and Z use US positions. ISO and Japanese layouts have differences and need
separate validation before support is claimed. Unused matrix slots are zeroed.

The [fusion-kbd project](https://github.com/magoomby/fusion-kbd) is a useful
independent reference for this controller. This application uses its own
implementation through Linux hidraw, keeping the normal HID driver attached.

## Reports

The extra leading zero below is the API's unnumbered report-ID placeholder;
it is not part of the eight-byte feature payload.

```text
Preset:        00 08 00 EFFECT SPEED BRIGHTNESS COLOR DIRECTION CHECKSUM
Custom upload: 00 12 00 01     08    00         00    00        CHECKSUM
```

Checksum is `255 - (sum(the seven payload header bytes) & 255)`.
Custom slot 1 contains 128 entries of `00 R G B`: 512 bytes in total.
Upload eight 64-byte output reports, each prefixed by the API report-ID zero,
then select custom effect `0x34`. Keep the vendor's 65 ms feature pacing and
100 ms output pacing. The UI maps 0–100% brightness to firmware values 0–50.

The indexed hardware palette is red, orange, yellow, green, blue, purple,
white (1–7). A live test confirmed that index 6 is purple on the reference
machine; a direct RGB `00 ff ff` upload was visually confirmed cyan with
normal typing intact. Arbitrary colors use direct RGB custom mode, while
hardware animations use the nearest indexed color.

The worker has an 8-second process deadline and a shared flock to prevent
overlap with boot/resume restore. There is no software animation stream or
keyboard-input capture; animated presets run in the keyboard firmware.

## Persistence

Applying a design writes it to the active controller. The app does not expose
an unverified flash-write command. Instead, a validated root-owned JSON profile
is reapplied by a system oneshot before the login screen and after suspend.
Do not call that permanent storage in the keyboard. A cold-boot/suspend test
must be performed on each additional hardware/firmware combination.

The names of the vendor's profile/startup methods are insufficient evidence:
some use a different 264-byte protocol for other keyboard families. This
implementation deliberately excludes those commands.
