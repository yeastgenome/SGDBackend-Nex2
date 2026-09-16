# AlphaFold structure thumbnails (Locus Summary Page)

The Protein section of the Locus Summary Page (SGDFrontend
`static/templates/locus.jinja2`) shows a static AlphaFold structure
thumbnail, clickable through to the locus's Protein tab.

## How it works

- Thumbnails are pre-rendered PNGs (800x600, ~100-200 KB), one per
  protein, colored with the standard AlphaFold pLDDT confidence scheme
  (blue = high confidence, orange = low).
- They are keyed by UniProt accession and served from a **stable** prefix
  on the frontend asset bucket:

      s3://sgd-prod-assets/alphafold-thumbnails/<uniprot_id>.png
      https://d1x6jdqbvd5dr.cloudfront.net/alphafold-thumbnails/<uniprot_id>.png

  This prefix is independent of the versioned per-deploy asset prefixes
  written by the frontend `npm run upload`, so frontend deploys never
  touch it.
- The template builds the URL from `locus.uniprot_id`. Loci without an
  AlphaFold model simply 404 and the `onerror` handler hides the image —
  missing thumbnails are cosmetic, never an error.

## When to update

Only when **AlphaFold DB publishes a new model version** (roughly every
1-3 years; the current models are v6, from the August 2025 release) or if
new yeast proteins gain UniProt accessions/models. There is deliberately
NO cron job: the source data changes too rarely, and the interactive
viewer on the Protein tab always loads the live latest AFDB model
regardless, so thumbnails can only ever be subtly (not misleadingly)
stale between refreshes.

## How to update

The canonical scripts live in **SGDFrontend** under
`build/alphafold_thumbnails/` (`batch_render.sh` + `render_af_thumb.py`).

1. Requirements (any machine, a laptop is fine — the full proteome
   renders in well under an hour):
   - PyMOL headless (`brew install pymol` / `apt install pymol`)
   - AWS CLI with a profile that can write to `sgd-prod-assets`
2. Edit `batch_render.sh` if needed:
   - update the proteome tar URL to the new AFDB version, e.g.
     `UP000002311_559292_YEAST_v7.tar` (listing:
     https://ftp.ebi.ac.uk/pub/databases/alphafold/latest/)
   - update the `--profile` if your writing profile is named differently
3. Run it:

       ./batch_render.sh

   It downloads the ~1 GB yeast proteome archive, extracts the PDB
   models, renders every structure in parallel, and `aws s3 sync`s the
   PNGs to the prefix above. Failures are listed in `failures.log`.
4. CloudFront caches these objects for ~1 month. Re-uploads under the
   same keys therefore roll out gradually within a month; to force an
   immediate refresh, issue an invalidation for
   `/alphafold-thumbnails/*` on the distribution serving
   `d1x6jdqbvd5dr.cloudfront.net`.
5. Verify: pick a locus and check both

       curl -sI https://d1x6jdqbvd5dr.cloudfront.net/alphafold-thumbnails/Q06551.png   # ERF2
       https://www.yeastgenome.org/locus/S000004236  (Protein section)

## History

- 2026-09: initial generation (v6 models, ~6k proteins), Redmine
  6663-6667 LSP protein enhancements.
