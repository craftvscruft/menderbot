import subprocess
import tempfile

def git_diff_head(staged=False):
    staged_arg = []
    if staged:
        staged_arg = ['--staged']
    args = ["git", "diff"] + staged_arg + ["HEAD", "--", ".", ":!Pipfile.lock"]
    return subprocess.check_output(args, text=True)


def git_commit(message):
    """Invoke git commit, allowing user to edit"""
    with tempfile.NamedTemporaryFile(mode='w+t', delete=True) as f:
        f.write(message)
        f.seek(0)
        args = ['git', 'commit', '--allow-empty', '--template', f.name]
        subprocess.run(args)
