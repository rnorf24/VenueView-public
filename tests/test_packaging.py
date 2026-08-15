import ast
import hashlib
import json
import subprocess
import sys

import venueview


def test_desktop_spec_files_are_valid_python(project_root):
    for relative_path in (
        "packaging/venueview.spec",
        "packaging/venueview_macos.spec",
    ):
        source = (project_root / relative_path).read_text(encoding="utf-8")
        ast.parse(source, filename=relative_path)


def test_macos_spec_builds_an_app_bundle_with_public_config(project_root):
    source = (project_root / "packaging/venueview_macos.spec").read_text(
        encoding="utf-8"
    )

    assert "BUNDLE(" in source
    assert 'name="VenueView.app"' in source
    assert 'bundle_identifier="com.venueview.desktop"' in source
    assert "datas=public_config" in source
    assert '"config/profiles"' in source
    assert '"config/rules"' in source
    assert 'config_root / "rules" / "public_rules.json"' in source
    assert 'icon=str(assets_root / "venueview.icns")' in source
    assert 'release_info["read_project_version"]' in source
    assert '"CFBundleShortVersionString": project_version' in source


def test_platform_build_scripts_bundle_python(project_root):
    windows = (project_root / "packaging/build_windows.ps1").read_text(encoding="utf-8")
    macos = (project_root / "packaging/build_macos.sh").read_text(encoding="utf-8")

    assert "pip install" in windows
    assert '".[build]"' in windows
    assert "venueview.spec" in windows
    assert ".venv-build-windows" in windows
    assert "generate_windows_version.py" in windows
    assert (project_root / "packaging/build_installer_windows.ps1").exists()
    assert "pip install" in macos
    assert '".[build]"' in macos
    assert "venueview_macos.spec" in macos
    assert "iconutil" in macos


def test_public_icon_assets_and_installer_definitions_exist(project_root):
    assets = project_root / "packaging/assets"
    assert (assets / "venueview.svg").read_text(encoding="utf-8").startswith("<svg")
    assert (assets / "venueview.png").stat().st_size > 0
    assert (assets / "venueview.ico").stat().st_size > 0
    assert (project_root / "packaging/installer/VenueView.iss").exists()
    mac_installer = (project_root / "packaging/build_installer_macos.sh").read_text(
        encoding="utf-8"
    )
    assert "pkgbuild" in mac_installer
    assert "hdiutil" in mac_installer
    assert 'ln -s /Applications "${staging}/Applications"' in mac_installer
    assert '-srcfolder "${staging}"' in mac_installer

    windows_installer = (
        project_root / "packaging/installer/VenueView.iss"
    ).read_text(encoding="utf-8")
    assert "PrivilegesRequired=lowest" in windows_installer
    assert "CloseApplications=yes" in windows_installer
    assert "RestartApplications=no" in windows_installer
    assert "Flags: unchecked" in windows_installer
    assert "CurUninstallStepChanged" in windows_installer
    assert "SuppressibleMsgBox" in windows_installer
    assert "private_rules.json" in windows_installer


def test_release_version_has_one_source_of_truth(project_root):
    result = subprocess.run(
        [sys.executable, project_root / "packaging/release_info.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == venueview.__version__

    checked = subprocess.run(
        [
            sys.executable,
            project_root / "packaging/release_info.py",
            "--check-tag",
            f"v{venueview.__version__}",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert checked.stdout.strip() == venueview.__version__


def test_windows_version_metadata_is_generated_from_project_version(
    project_root, tmp_path
):
    output = tmp_path / "version_info.txt"
    subprocess.run(
        [
            sys.executable,
            project_root / "packaging/generate_windows_version.py",
            "--output",
            output,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    content = output.read_text(encoding="utf-8")
    assert f"StringStruct('FileVersion', '{venueview.__version__}')" in content
    numeric = tuple(int(part) for part in venueview.__version__.split("-")[0].split(".")) + (0,)
    assert f"filevers={numeric}" in content


def test_public_packages_cannot_sweep_in_private_configuration(project_root):
    manifest = (project_root / "MANIFEST.in").read_text(encoding="utf-8")
    assert "recursive-include config *.json" not in manifest
    assert "config/rules/public_rules.json" in manifest

    for relative_path in (
        "packaging/venueview.spec",
        "packaging/venueview_macos.spec",
    ):
        source = (project_root / relative_path).read_text(encoding="utf-8")
        assert 'datas=[(str(config_root), "config")]' not in source
        assert "datas=public_config" in source
        assert "config/private" not in source
        assert 'VENUEVIEW_BUILD_EDITION", "public"' in source
        assert "VENUEVIEW_BUNDLED_PRIVATE_RULES" in source
        assert '"config/operational_defaults"' in source
        assert "must remain outside the project tree" in source

    assert (project_root / "packaging/build_private_release_macos.sh").exists()
    assert (project_root / "packaging/build_private_release_windows.ps1").exists()


def test_release_manifest_records_artifact_checksum(project_root, tmp_path):
    artifact = tmp_path / f"VenueView-{venueview.__version__}-synthetic-installer.bin"
    artifact.write_bytes(b"synthetic VenueView installer fixture")
    subprocess.run(
        [
            sys.executable,
            project_root / "packaging/write_release_manifest.py",
            "--platform",
            "SyntheticOS",
            "--architecture",
            "test64",
            tmp_path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = json.loads(
        (tmp_path / "release-manifest.json").read_text(encoding="utf-8")
    )
    expected_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert manifest["version"] == venueview.__version__
    assert manifest["edition"] == "public"
    assert manifest["trust_status"] == "unsigned-evaluation"
    assert manifest["artifacts"] == [
        {
            "filename": artifact.name,
            "sha256": expected_hash,
            "size_bytes": artifact.stat().st_size,
        }
    ]
    assert expected_hash in (tmp_path / "SHA256SUMS.txt").read_text(
        encoding="utf-8"
    )


def test_desktop_build_workflow_uses_native_runners_and_smoke_checks(project_root):
    workflow = (
        project_root / ".github/workflows/desktop-builds.yml"
    ).read_text(encoding="utf-8")
    assert "runs-on: macos-latest" in workflow
    assert "runs-on: windows-latest" in workflow
    assert "build_release_macos.sh" in workflow
    assert "build_release_windows.ps1" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "--check-tag" in workflow

    mac_release = (
        project_root / "packaging/build_release_macos.sh"
    ).read_text(encoding="utf-8")
    windows_release = (
        project_root / "packaging/build_release_windows.ps1"
    ).read_text(encoding="utf-8")
    assert "smoke_test_desktop.py" in mac_release
    assert "smoke_test_desktop.py" in windows_release
    assert "write_release_manifest.py" in mac_release
    assert "write_release_manifest.py" in windows_release


def test_production_builds_require_platform_trust(project_root):
    macos = (project_root / "packaging/build_production_release_macos.sh").read_text(
        encoding="utf-8"
    )
    windows = (
        project_root / "packaging/build_production_release_windows.ps1"
    ).read_text(encoding="utf-8")
    signer = (project_root / "packaging/sign_windows_artifact.ps1").read_text(
        encoding="utf-8"
    )

    assert "APPLE_APPLICATION_IDENTITY" in macos
    assert "APPLE_INSTALLER_IDENTITY" in macos
    assert "APPLE_NOTARY_PROFILE" in macos
    assert "notarytool submit" in macos
    assert "stapler validate" in macos
    assert "signed-and-notarized" in macos
    assert "WINDOWS_CERT_THUMBPRINT" in windows
    assert "VENUEVIEW_REQUIRE_SIGNING" in windows
    assert "signtool verify" in signer
    assert "WINDOWS_TIMESTAMP_URL" in signer
