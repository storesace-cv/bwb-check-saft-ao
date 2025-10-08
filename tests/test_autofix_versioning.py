import pytest

from saftao.commands.autofix_hard import next_version_paths as hard_next_version_paths
from saftao.commands.autofix_soft import next_version_paths as soft_next_version_paths


@pytest.mark.parametrize(
    "next_version",
    [soft_next_version_paths, hard_next_version_paths],
)
def test_next_version_paths_increment_from_existing_suffix(tmp_path, next_version):
    source = tmp_path / "5417087017_1_20250701_000000_20250731_235959_20251006095424_v.02.xml"
    source.touch()

    ok_path, bad_path, suffix = next_version(source, tmp_path)

    expected_stem = "5417087017_1_20250701_000000_20250731_235959_20251006095424"
    assert ok_path == tmp_path / f"{expected_stem}_v.03.xml"
    assert bad_path == tmp_path / f"{expected_stem}_v.03_invalido.xml"
    assert suffix == "_v.03"


@pytest.mark.parametrize(
    "next_version",
    [soft_next_version_paths, hard_next_version_paths],
)
def test_next_version_paths_skips_existing_versions(tmp_path, next_version):
    source = tmp_path / "SAFTAO_v.02_invalido.xml"
    source.touch()

    # Simulate already exported version 03
    (tmp_path / "SAFTAO_v.03.xml").touch()
    (tmp_path / "SAFTAO_v.03_invalido.xml").touch()

    ok_path, bad_path, suffix = next_version(source, tmp_path)

    assert ok_path == tmp_path / "SAFTAO_v.04.xml"
    assert bad_path == tmp_path / "SAFTAO_v.04_invalido.xml"
    assert suffix == "_v.04"
