#! /bin/sh

cd /data/www/SGDBackend-Nex2
source venv/bin/activate 
source prod_variables.sh 
python scripts/loading/ontology/go.py
python scripts/loading/reference/update_go_refs.py
python scripts/loading/go/load_gpad.py 'manually curated'
gpad_manual_status=$?
python scripts/loading/go/load_gpad.py computational
gpad_computational_status=$?
python scripts/loading/complex/addMissingLiterature.py

# GO-release author outreach: email authors of papers behind new gene-centric
# annotations, only when both GPAD loads succeeded (the sent log inside the
# pipeline guarantees no author is ever emailed twice for the same paper).
# MUST only run on sgd-curate: it holds the one canonical sent log, and its
# postfix relays through SES -- running elsewhere would double-email authors.
if [ "$(hostname)" != "ip-172-31-48-169" ]; then
    echo "not sgd-curate; skipping outreach emails"
elif [ $gpad_manual_status -eq 0 ] && [ $gpad_computational_status -eq 0 ]; then
    sh scripts/dumping/outreach/go_release_email_pipeline.sh --send
else
    echo "GPAD load failed (manual=$gpad_manual_status computational=$gpad_computational_status); skipping outreach emails"
fi
python scripts/dumping/curation/dump_go_annotations.py 
python scripts/dumping/curation/dump_gpad.py
python scripts/dumping/curation/dump_gpi.py
