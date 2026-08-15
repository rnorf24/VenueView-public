# VenueView icon assets

The approved 0.7.1 identity uses a calendar containing a small V nested inside
a larger V. The artwork is intentionally generic and contains no organization,
venue, event, client, sponsor, or agreement branding.

- `venueview.png` is the high-resolution raster source used by the macOS icon
  build.
- `venueview.ico` contains Windows sizes from 16 through 256 pixels.
- `venueview.svg` is the scalable public-source counterpart.
- `venueview.icns` is generated on macOS by `packaging/build_macos.sh` and is
  not a hand-maintained source file.

When the artwork changes, regenerate and inspect the Windows ICO at small
sizes, then rebuild the macOS ICNS on a Mac before creating installers.
