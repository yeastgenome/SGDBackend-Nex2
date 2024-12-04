#!/bin/sh

OUTPUT_FILE=/tmp/load-references-from-abc.out

echo "load-references-from-abc.sh start:  `/bin/date`" | /bin/tee $OUTPUT_FILE

cd /data/www/SGDBackend-Nex2
mkdir -p scripts/loading/reference/data
. venv/bin/activate

echo "----------" | /bin/tee -a $OUTPUT_FILE
echo "load_new_references_from_abc.py start:  `/bin/date`" | /bin/tee -a $OUTPUT_FILE
python scripts/loading/reference/load_new_references_from_abc.py | /bin/tee -a $OUTPUT_FILE

echo "----------" | /bin/tee -a $OUTPUT_FILE
echo " load_tet_from_abc.py start:  `/bin/date`" | /bin/tee -a $OUTPUT_FILE
python scripts/loading/reference/load_tet_from_abc.py | /bin/tee -a $OUTPUT_FILE

echo "----------" | /bin/tee -a $OUTPUT_FILE
echo "load-references-from-abc.sh end:  `/bin/date`" | /bin/tee -a $OUTPUT_FILE

/usr/bin/aws sns publish \
    --topic-arn $SNS_TOPIC_ARN \
    --subject "load-references-from-abc.sh completed" \
    --message file://${OUTPUT_FILE.out

echo "load-references-from-abc.sh start:  `/bin/date`" | /bin/tee $OUTPUT_FILE

cd /data/www/SGDBackend-Nex2
. venv/bin/activate

echo "----------" | /bin/tee -a $OUTPUT_FILE
echo "load_new_references_from_abc.py start:  `/bin/date`" | /bin/tee -a $OUTPUT_FILE
python scripts/loading/reference/load_new_references_from_abc.py | /bin/tee -a $OUTPUT_FILE

echo "----------" | /bin/tee -a $OUTPUT_FILE
echo " load_tet_from_abc.py start:  `/bin/date`" | /bin/tee -a $OUTPUT_FILE
python scripts/loading/reference/load_tet_from_abc.py | /bin/tee -a $OUTPUT_FILE

echo "----------" | /bin/tee -a $OUTPUT_FILE
echo "load-references-from-abc.sh end:  `/bin/date`" | /bin/tee -a $OUTPUT_FILE

/usr/bin/aws sns publish \
    --topic-arn $SNS_TOPIC_ARN \
    --subject "load-references-from-abc.sh completed" \
    --message file://${OUTPUT_FILE}
