# Install, Upgrade, Uninstall, and Rollback

These instructions are for signed production artifacts. Unsigned evaluation
builds remain pilot-only.

## macOS

Install by opening the notarized DMG and dragging **VenueView** into
**Applications**. Replace the existing application when upgrading; imported
organization settings live in the user's Application Support folder and remain
available to the new version.

To uninstall, quit VenueView and move **VenueView** from Applications to the
Trash. Imported settings are preserved by default. To remove the imported
settings too, first launch VenueView, choose **Restore built-in settings**, and
then remove the application. This deletes only VenueView's imported replacement
file and leaves the built-in private-edition settings inside the app unchanged.

## Windows

Run the signed setup executable. The per-user installer does not require
administrator rights and upgrades the existing VenueView installation in place.
Imported organization settings remain in the user's application-data folder.

Uninstall VenueView from **Settings > Apps > Installed apps**. The uninstaller
asks whether to remove the imported organization settings. Choose **No** to
preserve them for a later reinstall or **Yes** to delete only VenueView's
`private_rules.json` file for that Windows account.

## Rollback

1. Quit VenueView completely.
2. Uninstall the current application while preserving imported settings.
3. Verify the checksum and signature of the previously approved installer.
4. Install the prior version.
5. Launch it and confirm the organization-settings source and version shown in
   the interface.
6. Process only the synthetic acceptance calendar before resuming operational
   use.

If an imported settings file is incompatible with the older version, use
**Restore built-in settings** and contact the release owner. Never copy private
settings into the source repository or a public issue.
