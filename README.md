# solstice-deps

A mirror of the Windows build dependencies pinned by
[Solstice](https://github.com/udtren/Solstice)'s GitHub Actions build
(`build-tools/github-actions/windows-dependencies.lock.json`).

The packages are prebuilt by the KDE Krita team from
[krita-deps-management](https://invent.kde.org/packaging/krita-deps-management)
and published in the KDE package registry (invent.kde.org project 16406).
That registry keeps only recent builds, so a pinned lock stops working when
its packages are removed. This repository keeps a copy of each pinned set as
the assets of one release, unchanged.

- **Release tag:** the lock's `mirror.tag`, for example
  `deps-20261009-4aff6eb` (build date and source revision).
- **Assets:** `<package>-<version>.tar`, byte-identical to the registry's
  `archive.tar`. The Solstice lock records each size and SHA-256, and the
  Solstice build checks them whether it downloads from here or from KDE.
- **Sources:** each release's notes name the krita-deps-management revision;
  that revision's recipes name the upstream source of every library.
- **Licenses:** each library keeps its own license (Qt and many others LGPL,
  FFmpeg LGPL/GPL, Boost BSL, and so on), as distributed by KDE. Nothing here
  is relicensed. This mirror exists only to build Solstice reproducibly; it
  is not a general distribution of these libraries.

## Adding a set

After the Solstice lock is refreshed
(`build-tools/github-actions/refresh-dependency-lock.py`), run the
**Mirror Solstice dependencies** workflow with the Solstice ref that holds the
new lock. It downloads each package from the KDE registry, checks it against
the lock and uploads what the release does not have yet. Run it soon after
the refresh, while KDE still has the packages.

Solstice's weekly **Dependency lock check** workflow reports missing mirror
assets and packages that KDE has removed.
