import subprocess
import tempfile
from typing import Optional


def git_diff_head(staged=False) -> str:
    staged_arg = []
    if staged:
        staged_arg = ["--staged"]
    args = ["git", "diff"] + staged_arg + ["HEAD", "--", ".", ":!Pipfile.lock"]
    return subprocess.check_output(args, text=True)


def git_commit(message: str) -> None:
    """Invoke git commit, allowing user to edit"""
    with tempfile.NamedTemporaryFile(mode="w+t", delete=True) as f:
        f.write(message)
        f.seek(0)
        args = ["git", "commit", "--allow-empty", "--template", f.name]
        subprocess.run(args, check=True)


def git_show_top_level() -> Optional[str]:
    try:
        args = ["git", "rev-parse", "--show-toplevel"]
        return subprocess.check_output(
            args, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except subprocess.CalledProcessError:
        return None
