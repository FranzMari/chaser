import subprocess

def is_installed(pkgname):
    realname = exists(pkgname)
    if not realname:
        realname = pkgname
    return not subprocess.call(['pacman', '-Qi', realname],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def exists(pkgname):
    try:
        return subprocess.check_output(['pacman', '-Sp', '--print-format',
            '%n', pkgname], stderr=subprocess.DEVNULL).split().pop()
    except subprocess.CalledProcessError:
        return False

def list_unofficial():
    return [ l.split() for l in subprocess.check_output(['pacman',
        '-Qm']).decode().strip().split('\n') ]

def search(query):
    try:
        return subprocess.check_output(['pacman', '-Ss', '--color=always', '--', query]).decode().strip().split('\n')
    except subprocess.CalledProcessError:
        return ''
