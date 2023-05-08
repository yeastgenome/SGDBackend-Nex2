#!/bin/sh

OUTPUT_FILE=${LOG_FILE}

echo "data_dump.sh start:  `/bin/date`" | /bin/tee $OUTPUT_FILE

cd /data/www/SGDBackend-Nex2
. venv/bin/activate && \
    python scripts/dumping/curation/dump_gff.py 2>&1 | /bin/tee -a $OUTPUT_FILE

echo "data_dump.sh end:  `/bin/date`" | /bin/tee -a $OUTPUT_FILE

/usr/bin/aws sns publish \
    --topic-arn $SNS_TOPIC_ARN \
    --subject "dump_gff.py completed" \
    --message file://${OUTPUT_FILE} \
    --region $AWS_REGION
