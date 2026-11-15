# Working in coon-hub

## Scope and source of truth

This is a public, data-driven APK catalog for Coon on the IHU689G head unit
(Geely Coolray VN), not the Coon application or an APK build project.
There is no application build, development server, package installation step,
or separate unit-test/lint configuration in this repository.

- `hub.json` is the runtime source of truth, updated rolling on `main`. Vehicles
  fetch it directly from GitHub's raw endpoint without credentials. Making the
  repository private breaks catalog access.
- APK binaries live on GitHub Releases, not in Git. Do not commit APKs; the
  existing `apks/` ignore rule does not cover APKs at arbitrary paths.
- `apps/<package>.md` contains provenance, patch behavior, risks, verification
  status, and rollback instructions. Read the relevant note before changing an
  app entry. Build/patch sources and factory backups referenced there live in
  the separate `coolray-lab` repository, not here.
- `icons/<package>.webp` contains extracted app icons. README specifies 192px
  WebP, with PNG also supported. Icons are optional.
- `hub.schema.json` is the editor/tooling contract. `tools/validate.py` is the
  authoritative repository check and does not load or execute that schema.
  Keep both aligned when changing the catalog contract; changing this repo
  alone does not update the external Coon consumer.

## Checks and commands

Run from the repository root:

```bash
python3 tools/validate.py
python3 tools/validate.py --assets
bash -n tools/promote.sh
```

- The first command is the fast, offline catalog check: structure, business
  rules, referenced icon existence, and orphan icons. Python standard library
  only; no pip dependencies.
- `--assets` additionally downloads every release and factory APK, streams its
  SHA-256 and byte count, and compares them with the catalog. This can transfer
  hundreds of megabytes. It does not inspect APK manifests or signatures.
- `.github/workflows/validate.yml` runs the asset check on every push and pull
  request using Ubuntu and Python `3.x`. An offline pass does not establish
  that CI will pass: remote assets must also be accessible and unchanged.
- `bash -n` checks shell syntax without publishing anything. Do not run the
  promotion script as a test; it writes to GitHub Releases.
- For validator changes, exercise the fast check and relevant invalid cases
  using temporary catalog files. The supported form is
  `python3 tools/validate.py /path/to/catalog.json` (optionally `--assets`).
  Even with a custom catalog file, icon lookup and orphan checks use this
  repository's `icons/`, not the temporary file's directory.

## Runtime contract and change boundaries

Coon reads `hub.json`, resolves relative icon paths against the catalog base
URL, and downloads APKs from the absolute HTTPS URLs in release/factory
records. The catalog supplies size for progress/display and SHA-256 for install
integrity. Release assets use tags `hub-YYYY.MM.DD`; preserve existing asset
URLs and bytes because clients rely on their recorded digests.

- Keep only fields used for runtime decisions/display in the catalog. Put
  maintainer details in `apps/<package>.md`, not new catalog fields. Unknown
  keys are rejected at the root, app, factory, and release levels.
- `schemaVersion` is currently `1`. README documents that Coon rejects schema
  versions newer than it supports.
- Android package names are unique app identities and determine note/icon
  filenames. The promotion script sorts apps lexicographically by package.
- Releases must be strictly ascending by `versionCode`, with at most one
  release per app per ISO `releaseAt` date. Status is required and limited to
  `stable` or `beta`; tags are free-form display labels, not a closed enum.
- Version codes must come from the actual APK manifest. Neither the validator
  nor the promotion script verifies them against the manifest. Digests must be
  lowercase 64-character hex; sizes are byte counts of the exact hosted APK.
- The presence of `factory`, not a tag, identifies a system-app patch. Preserve
  the original factory APK and metadata for recovery. Patch release codes must
  encode a valid date as `YYYYMMDDnn`, with `nn` from `01` to `99`, and exceed
  the factory version code so rollback can uninstall the update and reveal the
  `/system` version. README also requires staying below Android's signed-int32
  maximum; the validator does not enforce that upper bound.
- Ordinary apps retain their own APK version codes and use normal uninstall
  for rollback. Do not apply the patch version-code convention to them.
- `requires` lists packages Coon warns about, not installation blockers. The
  validator checks package syntax and duplicates, not dependency availability
  or dependency graph correctness.
- Removing an icon reference or app requires removing any now-unused icon.
  Every non-hidden entry under `icons/` is checked for orphaning, so do not put
  unrelated files there. Naming/dimensions follow README conventions; the
  validator checks the path/extension and existence, not image dimensions or
  that the filename matches the package.

## Lifecycle and device verification

`postInstall` and `postRollback` accept only `reboot` or
`start-service:<package>/<class>`. Relative classes such as `.service.Foo`
use Android's flattened component syntax. Do not introduce arbitrary shell
hooks or additional actions without coordinating the consumer contract.

README describes the critical system-app lifecycle: installation or rollback
can kill all UID 1000 processes, including Coon. Coon records pending work
before committing, resumes after restart, then executes hooks sequentially,
stopping on the first error. Reboot requires user confirmation in Coon.
This behavior is implemented outside this repo; local validation cannot test it.

For AutoKeyServer specifically, consult `apps/com.flyme.auto.keyserver.md`:
both lifecycle hooks restart `AutoKeyService`. The documented patch forwards
GELLY/MODE events to `app.coon` with factory fallback. Its earlier
property-only release was withdrawn; do not restore it from old history.
The maintained release is beta pending full physical-button verification.
Do not equate digest/signature checks or simulated broadcasts with device
acceptance testing.

## Publishing: side effects and script limitations

Use `tools/promote.sh` only when release publication is intended. It targets
`g-e-n-v/coon-hub` explicitly, regardless of the checkout's Git remote.
Its usage examples are in README; flags are parsed in the script itself.

Example command shape for an existing ordinary app:

```bash
tools/promote.sh <package> /path/to/app.apk \
  --version-code <manifest-version-code> \
  --release-at YYYY-MM-DD --status beta --note "Release description"
```

- Requires Bash, Python 3, authenticated `gh`, `shasum`, and macOS/BSD
  `stat -f%z`. The publication script is not Linux-portable as written, even
  though validation CI runs on Ubuntu. Patch/factory publication additionally
  requires `keytool` and checks platform-testkey serial `b3998086d056cffa`.
- `--release-at` defaults to the local current date and determines both the
  catalog date and release tag. `--status` defaults to `stable`, so explicitly
  pass `--status beta` for unaccepted builds. New app entries require `--name`.
- `--factory` sets/replaces the factory record rather than adding a release.
  Register the factory before promoting a system patch: patch classification
  and the signature check depend on an existing factory or `--factory`.
- Asset names are `<package>-<versionCode>.apk`, or
  `<package>-factory-<versionCode>.apk` for factory uploads. The script computes
  digest/size, creates the release if needed, and uploads with `--clobber`.
- Upload happens **before** duplicate version/date checks and final catalog
  validation. A failed run may already have created a release or overwritten
  an asset; a validation failure may also leave `hub.json` modified. Inspect
  both remote assets and the local diff before retrying. This is not atomic.
- Repeated `--note`, `--requires`, `--post-install`, and `--post-rollback` flags
  are collected by Bash but joined with spaces and split on `|` in Python.
  Repetition does not reliably produce separate JSON elements as the usage
  suggests. Inspect the resulting arrays; manually editing `hub.json` avoids
  this serialization limitation. Repeated `--tag` values are passed separately.
- On existing entries, nonempty metadata flags replace the corresponding
  field, while omitted/empty values leave it unchanged. There is no flag for
  setting an icon or clearing these fields. Add icons and maintainer notes
  separately, and verify their consistency with the catalog.
- The script ends with offline validation only. It neither runs `--assets`
  nor commits/pushes the catalog, despite printing suggested Git commands.
  Publishing an asset does not itself update the catalog served from `main`.

## Editing conventions

Existing documentation, catalog copy, and validator diagnostics are primarily
Vietnamese. Preserve Unicode text and follow nearby terminology. Catalog JSON
uses two-space indentation, literal Unicode (`ensure_ascii=False` in the
publisher), and a trailing newline. Python validation helpers accumulate
messages through `err()` and report them together at CLI exit; publishing is
Bash with `set -euo pipefail` plus embedded Python for catalog updates.

For catalog changes, update the relevant maintainer note when provenance,
behavior, verification status, or rollback changes, then run the validator.
For contract changes, review `hub.schema.json`, validator key sets/checks,
promotion serialization, and README together rather than updating one in
isolation.
