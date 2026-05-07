from src.github_agent.phase1.models.schemas import TreeItem
from src.github_agent.phase1.services.filter_service import FilterService


def test_should_exclude_path_for_noise_and_large_files() -> None:
    service = FilterService(max_file_size_bytes=100)

    excluded, reasons = service.should_exclude_path("node_modules/react/index.js", size=50)
    assert excluded is True
    assert "excluded_directory" in reasons

    excluded, reasons = service.should_exclude_path("assets/logo.png", size=50)
    assert excluded is True
    assert "excluded_extension" in reasons

    excluded, reasons = service.should_exclude_path("fonts/agustina.otf", size=50)
    assert excluded is True
    assert "excluded_extension" in reasons

    excluded, reasons = service.should_exclude_path("src/generated.bundle.js", size=50)
    assert excluded is True
    assert "excluded_pattern" in reasons

    excluded, reasons = service.should_exclude_path("src/big_module.py", size=1000)
    assert excluded is True
    assert "file_too_large" in reasons


def test_filter_tree_splits_selected_and_filtered_files() -> None:
    service = FilterService(max_file_size_bytes=10_000)
    tree_items = [
        TreeItem(path="README.md", type="blob", size=100),
        TreeItem(path="package.json", type="blob", size=100),
        TreeItem(path="src/main.py", type="blob", size=100),
        TreeItem(path="tests/test_app.py", type="blob", size=100),
        TreeItem(path="node_modules/react/index.js", type="blob", size=100),
        TreeItem(path="assets/logo.png", type="blob", size=100),
    ]

    result = service.filter_tree(tree_items)

    assert result.filtered_out_count == 2
    assert "README.md" in result.selected_paths
    assert "package.json" in result.selected_paths
    assert "src/main.py" in result.selected_paths
    assert "tests/test_app.py" in result.selected_paths
    assert "assets/logo.png" in result.filtered_out_paths
