# Security policy

EasySlice Print runs inside Blender with the same permissions as Blender itself. It reads the
scene, creates objects and writes the files you export — nothing else, and it never contacts the
network.

If you find a security problem (for example a crafted `.blend` that makes the add-on execute
arbitrary code, or unsafe file handling in the export path), please **do not open a public
issue**. Email rafael.omodei@outlook.com with a description and reproduction steps; you will get
an answer within 7 days. Fixed versions are published as GitHub releases and noted in `CHANGELOG.md`.
