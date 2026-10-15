# citation-ledger

Claim-level provenance for grounded answers and documents. A small
stdlib-only Python 3 tool that owns the `url -> [n]` mapping so citation
numbers come from retrieval, never from the model's memory.

Mechanism provenance: the grounded-citation ledger pattern is adapted from the
Hermes `grounded-citations` skill (Hermes Agent + Teknium, MIT-licensed). This
is an independent, clean-room implementation.

## Why

An LLM that writes `[3]` from memory invents URLs and drifts numbering. If a
script issues the id the moment a page is fetched, and the model may only emit
ids the ledger handed it, then every citation resolves to a real retrieved URL
and `verify` can gate delivery mechanically.

Two provenance upgrades sit on top of plain numbering:

- **verbatim evidence** — attach a supporting quote to a source; the tool
  refuses it unless the exact wording literally appears in the fetched page
  text, whitespace/case/markdown-insensitive. A paraphrase cannot pass as
  evidence.
- **declared unknowns** — a load-bearing claim you genuinely could not source
  is marked `[unverified]` instead of being silently blended in, and the
  coverage check counts it as declared provenance.

## Requirements

Python 3.8+ (3.9 verified). Nothing else — standard library only. Runs on
macOS, Linux, and Windows.

## Ledger location

Resolution order (first one wins):

1. `--ledger PATH`
2. `$CITATION_LEDGER`
3. `<user cache dir>/citation-ledger/ledger.json` — `$XDG_CACHE_HOME` or
   `~/.cache` on macOS/Linux; `%LOCALAPPDATA%` on Windows.

## Quick start

```bash
python citation_ledger.py reset                  # clean ledger for a new task
python citation_ledger.py add https://example.org/a --title "A"   # prints [1]
python citation_ledger.py add https://example.org/b                # prints [2]
python citation_ledger.py list                    # ledger table
python citation_ledger.py render                  # Sources: block
python citation_ledger.py verify draft.md         # gate before delivery
```

`add` is idempotent and URL-normalized (fragment and trailing slash dropped):
the same page always returns the same id within a ledger, so ids stay stable
across many search/extract rounds.

## Commands

| Action | Command |
|---|---|
| Fresh ledger for a new task | `citation_ledger.py reset` |
| Register a source, get its id | `add <url> [--title T]` |
| Register several at once | `add <url1> <url2> ...` |
| Register from JSON tool output | `ingest results.json` (or `-` for stdin) |
| Attach verbatim evidence to a source | `note <id> --text "exact wording" --from page.txt` |
| Show ledger | `list [--json]` |
| Render the Sources block | `render [--style markdown\|plain\|evidence] [--only 1,3]` |
| Render only what a draft cites | `render --cited-in draft.md` |
| Check a draft's citations | `verify draft.md [--strict] [--min-coverage 0.6] [--require-evidence]` |

## The workflow it enforces

1. `reset` at the start of a task that will produce a grounded answer or
   document. Skip the reset when continuing work whose ids are already in a
   draft — reusing the ledger keeps the numbering stable.
2. **Register every source at retrieval time**, before writing prose. From a
   `web_search` / `web_extract` / fetch, pass the URLs to `add` (or pipe the
   raw JSON through `ingest`). Registering later, from memory, is the failure
   mode this tool exists to prevent.
3. **Cite while drafting.** Place bracketed id(s) right after the sentence the
   source supports: `Ice floats because it is less dense than liquid water.[1]`.
   Only ids the ledger returned — never invent an id or a URL.
4. **Append the Sources block** with `render --cited-in <draft>` so the id →
   URL mapping is generated mechanically, not retyped.
5. **Verify before delivering.** `verify` exits non-zero on unknown ids, a
   Sources block that disagrees with the ledger, or (with `--min-coverage`)
   prose that is too thinly cited.
6. **Fact-check mode.** For high-stakes work, `note` a verbatim quote per
   source, mark unsourceable claims `[unverified]`, and run
   `verify --require-evidence` so delivery fails if any cited source carries no
   quote. `render --style evidence` prints each source's quotes beneath its URL.

## Self-test

```bash
python selftest.py
```

Exercises: ids issued at retrieval time (idempotent), a paraphrased quote
rejected, a genuine verbatim quote accepted, `[unverified]` counted as declared
provenance, a correct draft passing verify, an unknown id failing verify, and
`--require-evidence` failing an unquoted cited source. Exit 0 = all passed.

## Pitfalls

- **Registering after writing** re-introduces the hallucinated-URL risk the
  numbering removes.
- **Renumbering mid-task.** Ids are ledger identities; `[4]` must stay that
  source. Only `reset` between tasks.
- **Retyping URLs into the Sources block.** Always `render`; a hand-typed URL
  is an unverified claim.
- **Quoting from a search snippet instead of the page.** Evidence quotes come
  from the extracted page text — save it, then `note --from` that file.
- **`[unverified]` as an escape hatch.** It marks the rare genuinely
  unsourceable claim; if most sentences carry it, the task needed more
  retrieval, not more markers.
- **Parallel workers.** Point them all at one ledger with `--ledger` (or
  `CITATION_LEDGER`), else their ids will collide.

## License

MIT — see [LICENSE](LICENSE).
