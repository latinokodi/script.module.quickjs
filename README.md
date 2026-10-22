# script.module.quickjs

Kodi module addon that embeds **QuickJS** (quickjs-ng) through a small C wrapper
(`src/wrapper.c`) exposed to Python via `ctypes` (`lib/qjs.py`).

`eval_script(js)` evaluates a script and returns the JS completion value as a
string.  This is what Kodi addons use to run embedded player / anti-bot
JavaScript without a browser or a JS engine Python package.

## Layout

```
addon.xml                  addon definition (xbmc.python module, lib/)
lib/qjs.py                 ctypes wrapper (pre-loads the shared libqjs dependency)
lib/<platform>/            native binaries shipped with the addon
src/wrapper.c              C bridge: eval_js_wrapper() / free_js_wrapper_result()
src/CMakeLists.txt         builds qjswrapper.* against ../../quickjs
.github/workflows/         CI that (re)builds all native binaries
.github/scripts/           smoke tests used by CI
```

## Platform support

| platform dir | wrapper | QuickJS library | notes |
|---|---|---|---|
| `windows_x86_64` | `qjswrapper.dll` | `qjs.dll` | MSVC build (Kodi ships the VC/UCRT runtime) |
| `linux_x86_64` | `libqjswrapper.so` | `libqjs.so.0` | wrapper `RPATH=$ORIGIN`; built on Ubuntu 22.04 (glibc) |
| `darwin_x86_64` | `libqjswrapper.dylib` | `libqjs.0.dylib` | wrapper `LC_LOAD_DYLIB @loader_path/libqjs.0.dylib` |
| `android_arm64` | `libqjswrapper.so` | — | statically linked (no extra library) |
| `android_armv7` | `libqjswrapper.so` | — | statically linked (no extra library) |

`lib/qjs.py` pre-loads the per-platform QuickJS library before loading the
wrapper (`_preload_dependency_library()`), so dynamic wrappers resolve on
Windows/Linux/macOS.  Android wrappers are self-contained.

Known upstream gaps: there is no Linux-ARM or macOS-arm64 wrapper in this repo;
callers must fall back to another JS path (e.g. a pure-Python unpacker) on those
devices until those platforms are added.

## Building the native binaries

The wrapper is built with CMake against [quickjs-ng](https://github.com/quickjs-ng/quickjs).
`src/CMakeLists.txt` resolves quickjs as a **sibling** directory of this repo
(`../../quickjs` relative to `src/`), so a local build looks like:

```bash
git clone https://github.com/quickjs-ng/quickjs.git ../quickjs
git -C ../quickjs checkout fd0a0210b7be00957751871e7e01b8291268fc29   # v0.15.1

# Windows (from a VS2022 developer prompt)
cmake -S src -B build -G "Visual Studio 17 2022" -A x64 -DBUILD_SHARED_LIBS=ON
cmake --build build --config Release --target qjswrapper --parallel

# Linux
cmake -S src -B build -DBUILD_SHARED_LIBS=ON -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_RPATH='$ORIGIN' -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON
cmake --build build --target qjswrapper --parallel

# macOS (x86_64 slice)
cmake -S src -B build -DBUILD_SHARED_LIBS=ON -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_OSX_ARCHITECTURES=x86_64 \
      -DCMAKE_INSTALL_NAME_DIR=@loader_path -DCMAKE_BUILD_WITH_INSTALL_NAME_DIR=ON
cmake --build build --target qjswrapper --parallel

# Android (arm64 example; requires NDK)
cmake -S src -B build -DCMAKE_TOOLCHAIN_FILE="$ANDROID_NDK/build/cmake/android.toolchain.cmake" \
      -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-21 \
      -DBUILD_SHARED_LIBS=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build build --target qjswrapper --parallel
```

After building, copy the produced `qjswrapper.*` + `qjs.*` into
`lib/<platform>/` using the names in the table above.  CI does this
automatically.

## CI

`.github/workflows/build-native.yml` builds all five platform binaries on
GitHub-hosted runners:

* `windows-latest` (MSVC), `ubuntu-22.04` (gcc), `macos-latest` (x86_64 cross
  build on the arm64 runner), `ubuntu-22.04` + Android NDK for arm64/armv7.
* quickjs-ng is pinned to commit `fd0a0210…` (v0.15.1) for reproducibility.
* Each job smoke-tests the result where the runner can execute it:
  Windows/Linux run `.github/scripts/load_test.py` through ctypes; macOS is
  checked structurally (`lipo`/`otool`); Android is checked to be a
  self-contained ELF (no external `libqjs`).
* The `package` job assembles the rebuilt `lib/<platform>/` tree, writes
  `SHA256SUMS`, zips the addon and publishes a
  `retrolatino-native-bundles.zip` drop-in for the Retro Latino addon.
* Artifacts are uploaded on every run; publishing a GitHub **release** attaches
  the addon zip + checksums to it.

Triggers: pull requests / pushes touching `src/`, `lib/qjs.py`, `addon.xml` or
the workflow itself, `workflow_dispatch`, and `release: published`.
