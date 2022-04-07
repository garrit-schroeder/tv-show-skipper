# Troubleshooting
If the `decode.py` script is killed while processing media you may encounter issues the next time you run it. This is because corrupt fingerprint files are likely left over from the killed session.
Simply remove the directory fingerprints before running the script again.

This can be avoided by using the "clean" flag `-c`, which clears the `/config/data/fingerprints` folder on startup and after completing.
This issue is mostly only relevant when running `decode.py` on its own. Using `jellyfin.py` avoids the need to manage the `fingerprints` folder manually
