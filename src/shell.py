import subprocess


def run_shell(command: str, shell: str = "/bin/bash") -> dict:
    result = subprocess.run(
        command,
        shell=True,
        executable=shell,
        text=True,
        capture_output=True,
        timeout=20,
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }
