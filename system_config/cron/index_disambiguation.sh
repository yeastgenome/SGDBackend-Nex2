#!/bin/sh

OUTPUT_FILE=/tmp/index_disambiguation.out

echo "index_disambiguation.sh start:  `/bin/date`" | /bin/tee $OUTPUt_FILE

cd /data/www/SGDBackend-Nex2
. venv/bin/activate && \
    python scripts/disambiguation/index_disambiguation.py | /bin/tee -a $OUTPUT_FILE

echo "index_disambiguation.sh end:  `/bin/date`" | /bin/tee -a $OUTPUT_FILE

/usr/local/bin/aws sns publish \
    --topic-arn "arn:aws:sns:us-west-2:172390527433:cron_jobs_qa" \
    --region us-west-2 \
    --message file://${OUTPUT_FILE}
