# IEA Team Portal v1.9.8 Release Checklist

## Release identity
- [x] `VERSION` is `1.9.8`.
- [x] README identifies v1.9.8 as the current version.
- [x] Release notes contain a consolidated final v1.9.8 section.
- [x] Footer documentation link resolves to the repository tag `v1.9.8` once that tag is published.

## Historical data workflow
- [x] Historical Data workspace available per season.
- [x] AccessIEA Rider Performance CSV auto-detection supported.
- [x] AccessIEA historical bootstrap supported for riders, memberships, classes, assignments, and IEA numbers.
- [x] Preview/validation occurs before writes.
- [x] Commit is atomic.
- [x] Duplicate historical results are skipped instead of overwritten.
- [x] Rider-specific historical result edit/delete supported.
- [x] Archived seasons remain available for historical corrections.

## Season lifecycle
- [x] Season status distinguishes Active, Open/Inactive, and Archived.
- [x] Archive readiness review checks operational and finance warnings.
- [x] Archive requires explicit confirmation.
- [x] Reopen does not automatically activate the season.
- [x] Archive/reopen and historical mutations are audited.

## Performance / UI
- [x] Season Archive counts use annotated queries.
- [x] Historical Data rider counts use annotated queries.
- [x] Historical import/readiness/correction screens include responsive/mobile treatment.

## Static release validation
- [x] Python AST parse passed.
- [x] Python compileall passed.
- [x] `bash -n portalctl` passed.
- [x] URL-to-view consistency passed.
- [x] Template named-route consistency passed.
- [x] ZIP integrity passed.
- [x] ZIP has the expected top-level release folder.

## Runtime validation
- [ ] Install/upgrade against the production-like Docker/PostgreSQL environment.
- [ ] Re-run an AccessIEA Rider Performance import with a real export.
- [ ] Verify historical result edit/delete after import.
- [ ] Exercise Archive Readiness with and without warnings.
- [ ] Verify footer `v1.9.8` link after publishing the GitHub tag.

> Note: Live Django/PostgreSQL runtime tests were not executed in the assistant build environment because Django is not installed there. Production/user acceptance testing remains required.
