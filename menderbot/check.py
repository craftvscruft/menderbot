import subprocess


def run_check(command):
    try:
        return (
            True,
            subprocess.check_output(
                command, stderr=subprocess.STDOUT, shell=True, text=True
            ),
        )
    except subprocess.CalledProcessError as e:
        return (False, e.output)
