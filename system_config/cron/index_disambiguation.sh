#!/bin/sh

OUTPUT_FILE=/tmp/index_disambiguation.out

echo "index_disambiguation.sh start:  `/bin/date`" | /bin/tee $OUTPUt_FILE

cd /data/www/SGDBackend-Nex2
. venv/bin/activate && \
    python scripts/disambiguation/index_disambiguation.py | /bin/tee -a $OUTPUT_FILE

echo "index_disambiguation.sh end:  `/bin/date`" | /bin/tee -a $OUTPUT_FILE

/bin/mail -s "index_disambiguation.sh: `/bin/date`" $CRON_EMAIL < $OUTPUT_FILE

if [ $? -eq 0 ]; then
    echo "email output sent"
else
    echo "email output not sent"
fi
