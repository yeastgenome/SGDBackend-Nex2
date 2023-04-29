#!/bin/sh

OUTPUT_FILE=/tmp/index_elasticsearch.out

echo "index_elasticsearch.sh start:  `/bin/date`" | /bin/tee $OUTPUT_FILE

cd /data/www/SGDBackend-Nex2

# elasticsearch 7 script
. venv/bin/activate && \
    python scripts/search/index_es_7.py | /bin/tee -a $OUTPUT_FILE

echo "index_elasticsearch.sh end:  `/bin/date`" | /bin/tee -a $OUTPUT_FILE

/usr/bin/aws sns publish \
    --topic-arn $SNS_TOPIC_ARN \
    --subject "index_elasticsearch.sh completed" \
    --message file://${OUTPUT_FILE}
