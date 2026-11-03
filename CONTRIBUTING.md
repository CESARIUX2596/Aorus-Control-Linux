# Contributing

Keep hardware claims specific to a USB ID, HID interface/descriptor, firmware,
and a tested laptop. Include `lsusb -d 1044:7a3f`, the relevant descriptor, and
observed behavior when reporting hardware issues; redact serial numbers.

Use `python3 server.py --demo` for interface development. Demo mode never
writes lighting commands. Python's standard library is sufficient; no npm
install or Python dependencies are needed.

Run `python3 -m unittest discover -s tests -v`, `node --check static/app.js`
(if Node is installed), and `sh -n install.sh uninstall.sh` before submitting.
Changes to wire reports need independently sourced packet fixtures and a
controlled test on matching hardware. Do not add driver detachments, arbitrary
USB device access, or speculative nonvolatile-memory writes.

Keep vendor installers, DLLs, captures, personal profiles, and raw analysis
bundles out of Git. Document protocol observations and their provenance in
`docs/PROTOCOL.md` instead. Do not run the web server as root or expand its
binding beyond loopback as a default.
