import io
import tarfile
import subprocess
import json
import re
import os

import requests
from toposort import toposort_flatten
import ccr

from chaser import pacman, prompt

def get_source_files(args, workingdir="."):
    """Download the source tarball and extract it"""
    try:
        pkgname = args.package
    except AttributeError:
        pkgname = args

    r = requests.get(ccr.getpkgurl(pkgname))
    tar = tarfile.open(mode='r', fileobj=io.BytesIO(r.content))
    tar.extractall(workingdir)

def recurse_depends(pkgname, graph=None):
    """Build a dependency graph"""
    if graph is None:
        graph = {}

    if graph.get(pkgname) is not None:
        # End case: already traversed
        return graph
    elif pacman.exists(pkgname):
        # End case: exists in pacman
        graph[pkgname] = set()
        return graph

    # Otherwise get dependencies
    graph[pkgname] = set()
    get_source_files(pkgname, ".")
    output = subprocess.check_output(["pkgvars.sh",
        "./{pkgname}/PKGBUILD".format(pkgname=pkgname)])
    data = json.loads(output.decode())['variables']
    # NOTE: We don't differentiate make/depends here, this is an area for
    # improvement in the future if someone cares.
    depends = data.get('makedepends', []) + data.get('depends', [])
    # Only depends that are not already installed
    for dep in depends:
        depname = re.split('[>=<]', dep)[0]
        if not pacman.is_installed(depname):
            graph[pkgname].add(depname)

    for dep in graph[pkgname]:
        recurse_depends(dep, graph)

    return graph

def dependency_chain(pkgname):
    """Return an ordered list of dependencies for a package"""
    depends = recurse_depends(pkgname)
    return toposort_flatten(depends)

def install(args):
    """Install a given package"""
    try:
        pkgname = args.package
    except AttributeError:
        pkgname = args

    editor = os.getenv('EDITOR')
    for package in dependency_chain(pkgname):
        # Ask to edit the PKGBUILD
        response = prompt.prompt("Edit {pkg} PKGBUILD with $EDITOR?".format(pkg=package))
        if response == prompt.YES:
            subprocess.call([editor, "./{pkg}/PKGBUILD".format(pkg=package)])
        # Ask to edit the .install, if it exists
        if os.path.isfile("./{pkg}/{pkg}.install".format(pkg=package)):
            response = prompt.prompt("Edit {pkg}.install with $EDITOR?".format(pkg=package))
            if response == prompt.YES:
                subprocess.call([editor, "./{pkg}/{pkg}.install".format(pkg=package)])
        # makepkg -i
        os.chdir(pkgname)
        subprocess.call(["makepkg", "-i"])
        os.chdir(os.pardir)

def check_updates(args):
    """Return list of (name, ver) tuples for packages with updates available"""
    installed = pacman.list_unofficial()
    updates = []
    for pkg in installed:
        pkgname, curver = pkg
        try:
            data = ccr.info(pkgname)
        except ccr.ccr.PackageNotFound:
            continue
        newver = data.get('Version', '0-0')
        pkgver, pkgrel = newver.split('-')
        if pkgver > curver.split('-')[0]:
            updates.append((pkgname, newver))
        elif pkgver == curver.split('-')[0] and pkgrel > curver.split('-')[1]:
            updates.append((pkgname, newver))

    return updates

def list_updates(args):
    """List currently installed unofficial packages in `name ver` format"""
    for name, ver in check_updates():
        print(name, ver)

def update(args):
    """Install updates"""
    updates = check_updates()
    print("Updates: {pkgs}".format(pkgs='  '.join([ '-'.join(p) for p in updates ])))
    response = prompt.prompt("Continue with installation?")
    if response == prompt.YES:
        for name, ver in updates:
            install(name)

def search(args):
    """Print search results"""
    try:
        query = args.query
    except AttributeError:
        query = args

    results = ccr.search(query)
    results.sort(key=lambda x: x.Name)
    for pkg in results:
        print("ccr/{name} {ver}".format(name=pkg.Name, ver=pkg.Version))
        print("    {desc}".format(desc=pkg.Description))

def info(args):
    """Print package info"""
    try:
        package = args.package
    except AttributeError:
        package = args

    try:
        results = ccr.info(package)
    except ccr.ccr.PackageNotFound:
        print("Package not found")
        return 1

    print("Name           : {name}".format(name=results.Name))
    print("Version        : {ver}".format(ver=results.Version))
    print("URL            : {url}".format(url=results.URL))
    print("Licenses       : {license}".format(license=results.License))
    print("Category       : {cat}".format(cat=results.Category))
    print("Votes          : {votes}".format(votes=results.NumVotes))
    print("Maintainer     : {name}".format(name=results.Maintainer))
    print("OutOfDate      : {val}".format(val=True if results.OutOfDate == '1' else False))
    print("Description    : {desc}".format(desc=results.Description))
