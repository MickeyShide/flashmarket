"""Safety contract for host memory protection deployment."""

from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "install-host-memory-protection.sh"


def test_installer_is_idempotent_and_refuses_unknown_swapfile() -> None:
    content = SCRIPT.read_text(encoding="utf-8")

    assert "swap_file=/swapfile" in content
    assert 'swap_type=$(blkid -p -s TYPE -o value "$swap_file"' in content
    assert 'if [ "$swap_type" != "swap" ]' in content
    assert "refusing to overwrite it" in content
    assert 'grep -Fxq "$swap_file"' in content
    assert "vm.swappiness=10" in content
