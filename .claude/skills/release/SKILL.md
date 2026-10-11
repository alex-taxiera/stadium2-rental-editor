---
name: release
description: Cut a release of the Stadium 2 rental editor patch - changelog entry, version tag, the draft GitHub release the workflow creates, attaching the locally built .bps and publishing. Use whenever the user wants to release, ship, publish, tag or cut a new version of the mod or patch, asks to bump the version, or asks to finish or fix a release that is still a draft, even if they do not say "release".
---

# Releasing the rental editor patch

A release is a GitHub release holding one file, `stadium2-rental-editor-us.bps`. Pushing a
`v*` tag makes `.github/workflows/mod-release.yml` draft it with notes; the patch is then
attached by hand, because building it takes the original ROM and GitHub has none.
"Releases" in `mod/NOTES.md` is the reference; this is the procedure.

Two things to hold on to throughout:

- **Only the patch is ever uploaded.** Never a `.z64`, the ELF, anything from `asm/`,
  `assets/`, `baseroms/` or `.emu/`. Those are the game itself or made from it, and
  putting one on a public release cannot be taken back.
- **Pushing the tag and publishing the draft are public.** Show the user the version and
  the notes and get a yes before the push, and ask again before publishing. Everything
  before the push is local and can be redone freely.

Find the remote of the user's own repository with `git remote -v` (`origin` is the
decompilation this is forked from and is read-only). Below it is called `<remote>`.

## 1. Is there something to release, and is the build the right one?

```bash
git status --short                       # must be clean, on rental-editor
git describe --tags --abbrev=0           # the last release, if any
git diff --stat <last-tag> -- mod/checksums.txt
python3 tools/mod/checksums.py check     # build/ against mod/checksums.txt
python3 -m unittest discover -s mod/tests
```

- If `mod/checksums.txt` has not changed since the last tag, the patch is byte for byte
  the one already released. Say so and ask whether a release is really wanted.
- If `check` reports a difference or a missing file, the build is stale or absent. It
  has to be rebuilt in WSL (`tools/mod/wsl_build.sh mod`, see "Building" in the notes),
  and `checksums.py update` run only if the mod's sources changed on purpose. Do not
  release around a failing check: the notes quote these checksums to users.
- If the mod's code changed since the last release, the emulator suite should have been
  run on this build (`python3 -m unittest discover -s mod/tests/emu`, Windows Python,
  about 6 minutes, BizHawk opens). Ask before starting it.

## 2. Version and changelog

Pick the version with the user if they did not give one: `vMAJOR.MINOR.PATCH`, and a
hyphenated tag such as `v0.2.0-rc1` for a pre-release. Add `## <version>` as the first
entry of `mod/CHANGELOG.md`.

Write the entry for someone who plays the mod: what they can now do, what was fixed,
what is still untested. Not commit subjects, addresses or tool changes. Work out what
changed from the previous entry, `mod/README.md` and the mod's commits
(`git log <last-tag>..HEAD -- mod tools/mod`). After a rebase onto a newer base that
range lists every commit of the mod again, so trust the previous changelog entry over
the log for what was already released.

```bash
python3 tools/mod/release_notes.py <version>
```

prints the notes exactly as they will be published. Show them to the user.

## 3. Commit, tag, push

Once the user agrees to the version and notes:

```bash
git commit -am "Changelog for <version>"
git tag <version>
git push <remote> rental-editor <version>
gh run watch $(gh run list --workflow mod-release.yml --event push --branch <version> --limit 1 --json databaseId --jq '.[0].databaseId') --exit-status
```

The run's `Draft the release` job creates the draft. If it fails because the changelog
has no entry for the tag, fix the changelog, commit, then move the tag:
`git tag -f <version>`, `git push <remote> :refs/tags/<version>`,
`git push <remote> rental-editor <version>`.

## 4. Attach the patch and publish

From the same checkout, with the tag's commit still checked out:

```bash
python3 tools/mod/checksums.py check
gh release upload <version> build/stadium2-rental-editor-us.bps
gh release view <version> --json isDraft,assets,url
```

Ask the user before publishing, then:

```bash
gh release edit <version> --draft=false
```

Publishing starts one last run (`Check the published patch`). It fails if anything but
the patch is attached or if the patch is not the one in the tag's `mod/checksums.txt`.
Watch it and report the result with the release's URL. If it fails, the wrong file is
public: replace it at once with `gh release upload <version> <patch> --clobber`, or
remove a stray file with `gh release delete-asset <version> <name>`, and re-run the job.
