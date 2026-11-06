from __future__ import annotations

from scripts import download_dataset


def test_kaggle_cli_is_found_beside_project_python(tmp_path, monkeypatch):
    scripts_dir = tmp_path / "Scripts"
    scripts_dir.mkdir()
    python_executable = scripts_dir / "python.exe"
    python_executable.touch()
    kaggle_executable = scripts_dir / "kaggle.exe"
    kaggle_executable.touch()
    monkeypatch.setattr(download_dataset.shutil, "which", lambda _: None)

    result = download_dataset.resolve_kaggle_cli(python_executable)

    assert result == str(kaggle_executable)


def test_kaggle_cli_falls_back_to_path_when_venv_cli_is_missing(tmp_path, monkeypatch):
    python_executable = tmp_path / "python.exe"
    python_executable.touch()
    monkeypatch.setattr(
        download_dataset.shutil,
        "which",
        lambda name: r"C:\Program Files\Kaggle\kaggle.exe" if name == "kaggle" else None,
    )

    result = download_dataset.resolve_kaggle_cli(python_executable)

    assert result == r"C:\Program Files\Kaggle\kaggle.exe"
