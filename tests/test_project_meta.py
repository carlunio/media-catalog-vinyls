from src.project_meta import get_app_meta


def test_project_meta_matches_current_release():
    meta = get_app_meta()

    assert meta.project_name == "media-catalog-vinyls"
    assert meta.version == "1.0.0"
    assert meta.changelog_path.name == "CHANGELOG.md"
