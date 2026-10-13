#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Solstice contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Mirror the KDE dependency packages pinned by a Solstice lock file.

Reads build-tools/github-actions/windows-dependencies.lock.json from the
Solstice repository at the given ref, and uploads every package that the
lock's mirror release does not have yet. Each archive is downloaded from the
KDE registry and checked against the lock's size and SHA-256 before it is
uploaded. Needs the GitHub CLI with permission to write releases.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

LOCK_PATH = 'build-tools/github-actions/windows-dependencies.lock.json'


def fetch(url, destination=None):
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Solstice-deps-mirror',
                                                           'Accept-Encoding': 'identity'})
            with urllib.request.urlopen(request, timeout=300) as response:
                if destination is None:
                    return response.read()
                with destination.open('wb') as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
                return None
        except Exception as error:
            if attempt == 3:
                raise
            print(f'  retry after {error}', flush=True)
            time.sleep(10 * (attempt + 1))


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def gh(*args, check=True):
    return subprocess.run(['gh', *args], check=check, capture_output=True, text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--solstice-repo', default='udtren/Solstice')
    parser.add_argument('--ref', required=True, help='Solstice branch, tag or commit')
    parser.add_argument('--work', type=Path, default=Path('work'))
    args = parser.parse_args()

    lock_url = f'https://raw.githubusercontent.com/{args.solstice_repo}/{args.ref}/{LOCK_PATH}'
    lock = json.loads(fetch(lock_url))
    mirror = lock.get('mirror')
    if not mirror:
        sys.exit(f'The lock at {args.ref} names no mirror')
    repository = os.environ.get('GITHUB_REPOSITORY', mirror['repository'])
    if repository != mirror['repository']:
        sys.exit(f"The lock mirrors to {mirror['repository']}, not {repository}")
    tag = mirror['tag']

    if gh('release', 'view', tag, '--repo', repository, check=False).returncode != 0:
        revisions = sorted({p['sourceRevision'] for p in lock['packages']})
        notes = (f'Windows build dependencies pinned by {args.solstice_repo} at `{args.ref}` '
                 f'({len(lock["packages"])} packages from the KDE registry, project '
                 f'{lock["registryProject"]}; krita-deps-management revision(s) '
                 f'{", ".join(r[:12] for r in revisions)}). Each archive matches the lock\'s '
                 'size and SHA-256. Sources: https://invent.kde.org/packaging/krita-deps-management '
                 'at the revision above; see the README for licenses.')
        gh('release', 'create', tag, '--repo', repository, '--title', tag, '--notes', notes)
        print(f'Created release {tag}', flush=True)

    existing = json.loads(gh('release', 'view', tag, '--repo', repository, '--json', 'assets').stdout)
    have = {asset['name']: asset['size'] for asset in existing['assets']}

    args.work.mkdir(parents=True, exist_ok=True)
    uploaded = 0
    for index, package in enumerate(lock['packages'], 1):
        name = Path(package['mirrorUrl']).name
        if have.get(name) == package['size']:
            continue
        if name in have:
            gh('release', 'delete-asset', tag, name, '--repo', repository, '--yes')
        print(f'[{index}/{len(lock["packages"])}] {name}', flush=True)
        archive = args.work / name
        fetch(package['url'], archive)
        if archive.stat().st_size != package['size'] or sha256(archive) != package['sha256']:
            sys.exit(f'{name}: size or SHA-256 differs from the lock; not uploaded')
        gh('release', 'upload', tag, str(archive), '--repo', repository)
        archive.unlink()
        uploaded += 1

    final = json.loads(gh('release', 'view', tag, '--repo', repository, '--json', 'assets').stdout)
    sizes = {asset['name']: asset['size'] for asset in final['assets']}
    missing = [p['mirrorUrl'] for p in lock['packages'] if sizes.get(Path(p['mirrorUrl']).name) != p['size']]
    if missing:
        sys.exit('Missing after upload: ' + ', '.join(missing))
    print(f'{tag}: {len(lock["packages"])} packages present, {uploaded} uploaded now', flush=True)


if __name__ == '__main__':
    main()
