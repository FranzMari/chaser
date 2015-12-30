import subprocess

def is_installed(pkgname):
    realname = exists(pkgname)
    if realname:
        return not subprocess.call(['pacman', '-Qi', realname],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return False

def exists(pkgname):
    try:
        return subprocess.check_output(['pacman', '-Sp', '--print-format',
            '%n', pkgname], stderr=subprocess.DEVNULL).split().pop()
    except subprocess.CalledProcessError:
        return False
