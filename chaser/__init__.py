__version__ = "0.1"

import io
import tarfile
import subprocess
import json

import requests
from toposort import toposort_flatten
import ccr

def get_source_files(pkgname, workingdir):
    """Download the source tarball and extract it"""
    r = requests.get(ccr.getpkgurl(pkgname))
    tar = tarfile.open(mode='r', fileobj=io.BytesIO(r.content))
    tar.extractall(workingdir)

def _depends(pkgname):
    get_source_files(pkgname, ".")
    output = subprocess.run(["pkgvars.sh", "./{pkgname}".format(pkgname=pkgname)],
            stdout=subprocess.PIPE)
    data = json.loads(output)['variables']
    return data['makedepends'] + data['depends']

def dependency_chain(pkgname):
    """Return an ordered list of dependencies for a package"""
    depends = {
        pkgname: _depends(pkgname),
    }
    for dep in depends[pkgname]:
        depends[dep] = _depends(dep)
    return toposort_flatten(depends)