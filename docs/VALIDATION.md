# Validation record

Date: November 3, 2026.

Reference system: GIGABYTE AORUS 15P YD, Fedora 43 KDE, keyboard USB
`1044:7a3f`, revision 1.30, lighting interface 3.

| Check | Result |
| --- | --- |
| USB ID, exact HID descriptor, 64-byte OUT endpoint | Matched |
| Native HID feature and custom RGB reports | Accepted by the device |
| Direct RGB cyan (`#00ffff`) | User visually confirmed turquoise/cyan; typing remained normal |
| Indexed palette discrepancy | Index 6 appeared purple; palette corrected and regression tested |
| Custom Aurora upload | Completed successfully |
| Installed local API: Save to keyboard | Applied design and returned `remembered: true` |
| Root-owned startup JSON | Existing Night runner profile preserved across the update |
| System restoration service | Enabled; ran successfully with `status=0/SUCCESS` |
| Desktop web service | Enabled; running on `127.0.0.1:8765` |
| Automated unit/API tests | 22 passed |
| Theme library | 30 unique presets with distinct outputs |
| Gaming contrast | Full movement colors, independently dimmed background, background-off behavior tested |
| Physical US/ANSI preview | Compared with owner-provided AORUS 15P image; 19-key top row, real numpad spans and offset arrows |
| Thumbnail color parity | Same renderer as the device payload, including painted keys and background glow |
| Browser workflow | Themes, brightness, painting, profile save/load/delete, apply, startup toggle, filters passed in demo mode |
| Mobile layout | 390 px viewport, no document overflow |
| Browser console and requests | No JavaScript errors or external requests in the workflow test |
| Upgrade compatibility | Old API version and missing key-span metadata were rejected before drawing; page recovered automatically with the current service |
| Installed version 1.1.1 | 101 colored keys, zero rendered overlaps, 30 themes, no JavaScript errors; startup file checksum unchanged |
| Python/JavaScript/shell syntax | Passed |
| Full reboot and actual suspend/resume cycle | Not performed; the service and resume hook are installed, but end-to-end cycle timing remains to be verified |
| Every physical key and animated effect | Not individually verified |

The boot-restoration service is a oneshot: `inactive (dead)` after a successful
run is expected. Check its exit status and journal rather than expecting it to
remain running. The desktop web service stays active.

The desktop service must not use a private user/filesystem namespace or
`NoNewPrivileges=yes`: it needs to invoke the exact, validated boot-profile
save helper through its narrow sudo rule. The separate root restoration
oneshot uses `NoNewPrivileges`, read-only filesystem protection, and no
network access. The browser server remains an ordinary desktop-user process.

This record establishes operation on the reference machine, not universal
compatibility across all AORUS/AERO keyboards or firmware revisions.

The installer stops the desktop service before replacing application files.
Versioned assets and the frontend's layout compatibility check prevent mixed
versions from drawing overlapping or uncolored keys during an update.
