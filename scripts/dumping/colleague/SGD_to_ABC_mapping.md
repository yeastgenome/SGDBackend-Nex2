# SGD colleague data → ABC mapping

Maps SGD `nex.*` colleague data to ABC (`agr_literature_service`) `person` /
`laboratory` / `person_lineage` tables.

- **Dump:** `SGDBackend-Nex2/scripts/dumping/colleague/dumpColleague.py` →
  single JSON file.
- **Load:** `agr_literature_service/lit_processing/oneoff_scripts/load_sgd_colleagues.py`
  (reads the JSON via `--datafile`; no longer connects to SGD directly).

The **Transform** column notes how the loader derives each value.

## 1. `colleague` → `person`

| SGD `nex.colleague` | Transform | ABC `person` |
|---|---|---|
| `display_name` (fallback `first_name`+`last_name`, else `Colleague <id>`); `suffix` appended | `display_name_for()` | `display_name` |
| — | minted via MATI (`get_next_person_curie`) | `curie` |
| `institution` | wrapped as 1-element array | `institution` |
| `colleague_url` where `url_type='Research summary'` | list | `webpage` |
| `city` / `state` / `postal_code` / `country` | trimmed | `city` / `state` / `postal_code` / `country` |
| `address1`, `address2`, `address3` | joined with ", " | `street_address` |
| `profession` + `research_interest` + `colleague_keyword`→`keyword.display_name` | `build_biography()` (`"Profession: X"` line, then research interest, then `"Keywords: a; b"`) | `biography_research_interest` |
| `display_email` | `true→show_all`, `false→hide_email` | `privacy` |

## 2. `colleague` → `person_name`

| SGD `nex.colleague` | Transform | ABC `person_name` |
|---|---|---|
| `first_name` / `middle_name` / `last_name` (last falls back to `display_name`) | primary row | `first_name` / `middle_name` / `last_name`, `is_primary=true` |
| `other_last_name` (+ `first_name`) | secondary row, only if present | `first_name` / `last_name`, `is_primary=false` |

## 3. `colleague` → `person_email` / `person_note`

| SGD `nex.colleague` | Transform | ABC target |
|---|---|---|
| `email` | only if present | `person_email.email_address` |
| `colleague_note` | only if present | `person_note.note` |

## 4. `colleague` → `person_cross_reference`

| SGD source | Transform | ABC `person_cross_reference` |
|---|---|---|
| `colleague_id` | `SGD:Colleague_<id>`, prefix `SGD` | `curie` / `curie_prefix` (idempotency key) |
| `obj_url` | 1-element array | `pages` (on the SGD xref) |
| `orcid` | normalized → `ORCID:<id>`, prefix `ORCID`; **skipped if curie already exists globally** | `curie` / `curie_prefix` |

`person_cross_reference.curie` is globally unique (`uq_person_xref_curie`): an
ORCID may already belong to an existing ABC person (e.g. AGR staff who are also
SGD colleagues), and two SGD colleagues can share an ORCID — colliding ORCID
xrefs are skipped and reported.

## 5. `colleague_relation` 'Head of Lab' → `laboratory` (one per distinct PI)

| SGD source | Transform | ABC `laboratory` |
|---|---|---|
| PI `colleague.display_name` | `"<name> Lab"` | `name` |
| — | minted (`get_next_laboratory_curie`) | `curie` |
| PI `colleague.institution` | 1-element array | `institution` |
| `colleague_url` where `url_type='Lab'` (PI) | list | `webpage` |
| PI `city` / `state` / `postal_code` / `country` / `address1-3` | | `city` / `state` / `postal_code` / `country` / `street_address` |
| — | constant | `status='active'` |
| PI `colleague_id` | `SGD:Lab_<pi_id>`, prefix `SGD` | `laboratory_cross_reference.curie` / `curie_prefix` (idempotency key) |

Lab strategy: one `laboratory` per distinct "Head of Lab" PI found in
`nex.colleague_relation`, not per `colleague.is_pi` flag.

## 6. `colleague_relation` 'Head of Lab' → `laboratory_person`

| SGD source | Transform | ABC `laboratory_person` |
|---|---|---|
| PI ↔ lab | PI row | `is_pi=<timestamp>`, `lab_position` = PI `job_title` or `"Principal Investigator"` |
| member ↔ lab (`colleague_id` → PI `associate_id`) | member row | `lab_position` = member `job_title` |

## 7. `colleague_relation` 'Associate' → `person_lineage`

| SGD source | Transform | ABC `person_lineage` |
|---|---|---|
| the two `colleague_id`s → person_ids | normalized to ascending person-id (symmetric) | `person_subject_id` / `person_object_id` |
| — | constant | `relationship='collaborator_of'` |

`collaborator_of` is a **symmetric** `PersonPersonRole`: SGD stores Associate
relations mirrored (both A→B and B→A), so the dump dedups them to one unordered
pair (`DISTINCT least/greatest`) and the loader normalizes each pair to ascending
person-id order. Dedups against `uq_person_lineage_person_ids_relationship`
(`person_subject_id`, `person_object_id`, `relationship`); self-pairs rejected.
4,540 mirrored rows → 2,276 deduped pairs.

## Skipped / dropped (no clean ABC target)

| SGD source | Disposition |
|---|---|
| `colleague_locus` (gene links) | skipped, count reported in dump metadata |
| phone numbers, `is_beta_tester` | dropped |
| `colleague_reference`, `colleaguetriage` | empty in source |

## Incremental sync (add / update / delete)

The loader is a re-runnable sync keyed on `colleague_id` (via the
`SGD:Colleague_<id>` xref), so it can run whenever SGD data changes:

- **add** — a colleague new to ABC is created.
- **update** — a matched colleague's `person` fields and child rows
  (names, email, note, ORCID xref, SGD-xref pages) are overwritten from SGD
  (SGD is the source of truth); only rows that actually differ are written.
- **delete** — with `--prune` on a full run, persons/labs/collaborator_of edges
  whose `colleague_id` left the SGD dump are removed. Guards: a person linked to
  a `users` account and a lab with `laboratory_allele_designation` rows are
  never hard-deleted; collaborator_of deletes only touch edges between two SGD
  persons.

Match keys: `SGD:Colleague_<id>` (person), `SGD:Lab_<pi_id>` (laboratory),
`(laboratory_id, person_id)` (laboratory_person), and
`(person_subject_id, person_object_id, relationship)` (person_lineage). Re-runs
are convergent: a run with no SGD changes is a no-op.

## Email de-duplication

A colleague new to ABC whose email already belongs to a pre-existing **non-SGD**
person (e.g. AGR staff/author) is attached to that person — its
`SGD:Colleague` xref is added and its fields synced — instead of creating a
duplicate. Matching is restricted to non-SGD persons because institutional
emails are shared by distinct colleagues, so a blanket email match would
wrongly merge different people.

`--merge-email-dups` repairs duplicates that already exist: for an email shared
by exactly one non-SGD and one SGD person, the SGD person's xrefs, lab
memberships and lineage edges are moved onto the kept person and the SGD
duplicate is deleted. Ambiguous groups (shared institutional emails, or two SGD
records for the same person) are reported and left untouched.
