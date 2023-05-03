#!/bin/sh

OUTPUT_FILE=/tmp/data_dump.out

echo "data_dump.sh start:  `/bin/date`" | /bin/tee $OUTPUT_FILE

cd /data/www/SGDBackend-Nex2
. venv/bin/activate && \
    python scripts/dumping/curation/dump_gff.py | /bin/tee -a $OUTPUT_FILE

echo "data_dump.sh end:  `/bin/date`" | /bin/tee -a $OUTPUT_FILE

/usr/bin/aws sns publish \
    --topic-arn $SNS_TOPIC_ARN \
    --subject "dump_gff.py completed" \
    --message file://${OUTPUT_FILE} \
    --region $AWS_REGION
