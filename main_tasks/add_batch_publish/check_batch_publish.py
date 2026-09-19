import hashlib
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path


REPOSITORY = Path("/var/lib/package-repository")
APPROVAL = Path("/app/approved.txt")


def snapshot(paths: list[Path]) -> dict[str, tuple[int, str]]:
    records = {}
    for root in paths:
        entries = [root, *root.rglob("*")] if root.is_dir() else [root]
        for path in entries:
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                value = os.readlink(path)
            elif stat.S_ISREG(mode):
                value = hashlib.sha256(path.read_bytes()).hexdigest()
            else:
                value = ""
            records[str(path)] = (mode, value)
    return records


def build_package(directory: Path, package: str) -> Path:
    staging = directory / f"build-{package}"
    (staging / "DEBIAN").mkdir(parents=True)
    (staging / "DEBIAN/control").write_text(
        f"Package: {package}\nVersion: 2.0\nArchitecture: all\n"
        "Maintainer: Packaging QA <qa@example.invalid>\n"
        "Description: Batch publication fixture\n"
    )
    artifact = directory / f"{package}_2.0_all.deb"
    subprocess.run(
        ["dpkg-deb", "--root-owner-group", "--build", str(staging), str(artifact)],
        check=True,
        capture_output=True,
        timeout=15,
    )
    shutil.rmtree(staging)
    return artifact


def run_batch(directory: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/app/repoctl.sh", "publish-batch", str(directory)],
        capture_output=True,
        text=True,
        timeout=30,
    )


def restore_repository(backup: Path) -> None:
    for path in REPOSITORY.iterdir():
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
    for path in backup.iterdir():
        destination = REPOSITORY / path.name
        if path.is_dir() and not path.is_symlink():
            shutil.copytree(path, destination, symlinks=True)
        elif path.is_symlink():
            destination.symlink_to(os.readlink(path))
        else:
            shutil.copy2(path, destination)


def check() -> None:
    approval_bytes = APPROVAL.read_bytes()
    approval_mode = APPROVAL.stat().st_mode
    with tempfile.TemporaryDirectory(prefix="batch-publish-check-") as temporary:
        work = Path(temporary)
        backup = work / "repository-backup"
        shutil.copytree(REPOSITORY, backup, symlinks=True)
        try:
            APPROVAL.write_bytes(approval_bytes + b"\nbatch-approved\n")

            invalid_batch = work / "invalid batch"
            invalid_batch.mkdir()
            build_package(invalid_batch, "batch-approved")
            (invalid_batch / "batch-broken_2.0_all.deb").write_text(
                "not a Debian package\n"
            )
            before = snapshot([REPOSITORY, APPROVAL, invalid_batch])
            invalid = run_batch(invalid_batch)
            assert invalid.returncode != 0 and invalid.stderr and not invalid.stdout, (
                "Malformed batch did not follow the failure contract"
            )
            assert snapshot([REPOSITORY, APPROVAL, invalid_batch]) == before, (
                "Malformed batch changed protected state"
            )

            empty_batch = work / "empty batch"
            empty_batch.mkdir()
            before = snapshot([REPOSITORY, APPROVAL, empty_batch])
            empty = run_batch(empty_batch)
            assert empty.returncode != 0 and empty.stderr and not empty.stdout, (
                "Empty batch did not follow the failure contract"
            )
            assert snapshot([REPOSITORY, APPROVAL, empty_batch]) == before, (
                "Empty batch changed protected state"
            )

            valid_batch = work / "valid batch with spaces"
            valid_batch.mkdir()
            approved = build_package(valid_batch, "batch-approved")
            rejected = build_package(valid_batch, "batch-rejected")
            input_hashes = {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (approved, rejected)
            }
            approval_before = APPROVAL.read_bytes()
            log_before = (REPOSITORY / "publish.log").read_bytes()

            result = run_batch(valid_batch)
            expected = "batch-approved\tAPPROVED\nbatch-rejected\tQUARANTINED\n"
            assert result.returncode == 0, result.stderr.strip()
            assert result.stdout == expected and not result.stderr, (
                f"Unexpected batch output: {result.stdout!r} {result.stderr!r}"
            )
            assert APPROVAL.read_bytes() == approval_before, "Approval file changed"
            assert {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (approved, rejected)
            } == input_hashes, "Input artifacts changed"

            public_artifact = REPOSITORY / "public/pool/batch-approved_2.0_all.deb"
            quarantine_artifact = REPOSITORY / "quarantine/batch-rejected_2.0_all.deb"
            wrong_public = REPOSITORY / "public/pool/batch-rejected_2.0_all.deb"
            assert public_artifact.read_bytes() == approved.read_bytes(), (
                "Approved package bytes are missing from the public pool"
            )
            assert quarantine_artifact.read_bytes() == rejected.read_bytes(), (
                "Rejected package bytes are missing from quarantine"
            )
            assert not wrong_public.exists(), "Rejected package entered the public pool"
            assert (REPOSITORY / "publish.log").read_bytes() == (
                log_before + expected.encode()
            ), "Publication log entries are incorrect"

            packages = (REPOSITORY / "public/Packages").read_text()
            assert "Package: batch-approved\n" in packages, (
                "Approved package is absent from the repository index"
            )
            assert "Package: batch-rejected\n" not in packages, (
                "Rejected package is present in the repository index"
            )
        finally:
            APPROVAL.write_bytes(approval_bytes)
            APPROVAL.chmod(approval_mode)
            restore_repository(backup)


if __name__ == "__main__":
    try:
        check()
    except (AssertionError, OSError, subprocess.SubprocessError) as error:
        print(f"INCORRECT: {error}")
    else:
        print(
            "CORRECT: Batch ordering, classification, artifacts, logs, indexing, "
            "input preservation, and failure atomicity passed"
        )
