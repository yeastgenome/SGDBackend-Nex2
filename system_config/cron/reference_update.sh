#! /bin/sh -x

OUTPUT_FILE=/tmp/output.log
MESSAGE_JSON_FILE=/tmp/message.json

echo "DEBUG: OUTPUT_FILE is $OUTPUT_FILE"
echo "DEBUG: LOG_FILE is $LOG_FILE"
echo "DEBUG: MESSAGE_JSON_FILE is $MESSAGE_JSON_FILE"

cd /data/www/SGDBackend-Nex2
. venv/bin/activate 

echo "reference_update.sh start:  `/bin/date`" | /bin/tee $OUTPUT_FILE

echo "DEBUG:  starting reference_update_from_abc.py"

/usr/bin/cp /dev/null $LOG_FILE
python /data/www/SGDBackend-Nex2/scripts/loading/reference/reference_update_from_abc.py | /usr/bin/tee -a $OUTPUT_FILE
cat $LOG_FILE >> $OUTPUT_FILE

echo "DEBUG:  end reference_update_from_abc.py"
echo "DEBUG:  starting reference_display_name_update.py"

/usr/bin/cp /dev/null $LOG_FILE
python /data/www/SGDBackend-Nex2/scripts/loading/reference/reference_display_name_update.py | /usr/bin/tee -a $OUTPUT_FILE
cat $LOG_FILE >> $OUTPUT_FILE

echo "DEBUG:  end reference_display_name_update.py"
echo "DEBUG:  starting dump_gene_pmid_pair.py"

/usr/bin/cp /dev/null $LOG_FILE
python /data/www/SGDBackend-Nex2/scripts/dumping/ncbi/dump_gene_pmid_pair.py | /usr/bin/tee -a $OUTPUT_FILE
cat $LOG_FILE >> $OUTPUT_FILE

echo "DEBUG:  end dump_gene_pmid_pair.py"

echo "DEBUG: OUTPUT_FILE before sed"

cat $OUTPUT_FILE

/usr/bin/sed -i 's/$/\\n/' $OUTPUT_FILE

echo "DEBUG: OUTPUT_FILE after sed"

cat $OUTPUT_FILE

echo '{"Data": "From: '$(echo $EMAIL_FROM)'\nTo: '$(echo $EMAIL_TO)'\nSubject: reference_update.sh report\nMIME-Version: 1.0\nContent-type: Multipart/Mixed; boundary=\"NextPart\"\n\n--NextPart\nContent-Type: text/plain\n\ndata_dump.sh completed successfully\n\n--NextPart\nContent-Type: text/plain;\nContent-Disposition: attachment; filename=\"reference_update_report.txt\"\n\n'$(cat $OUTPUT_FILE)'\n--NextPart--"}' > $MESSAGE_JSON_FILE

cat $MESSAGE_JSON_FILE

export AWS_REGION=$AWS_SES_REGION

/usr/local/bin/aws ses send-raw-email --cli-binary-format raw-in-base64-out --raw-message file://${MESSAGE_JSON_FILE} --debug

exit 0
