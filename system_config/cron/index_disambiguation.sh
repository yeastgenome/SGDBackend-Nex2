#!/bin/sh

OUTPUT_FILE=/tmp/index_disambiguation.out

echo "index_disambiguation.sh start:  `/bin/date`" | /bin/tee $OUTPUT_FILE

cd /data/www/SGDBackend-Nex2
. venv/bin/activate && \
    python scripts/disambiguation/index_disambiguation.py | /bin/tee -a $OUTPUT_FILE

echo "index_disambiguation.sh end:  `/bin/date`" | /bin/tee -a $OUTPUT_FILE

/usr/bin/aws sns publish \
    --topic-arn $SNS_TOPIC_ARN \
    --subject "index_disambiguation.py completed" \
    --message file://${OUTPUT_FILE}
