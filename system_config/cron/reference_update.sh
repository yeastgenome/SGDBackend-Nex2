#! /bin/sh -x

OUTPUT_FILE="/tmp/output.log"
LOG_FILE="/data/www/SGDBackend-Nex2/scripts/loading/reference/logs/reference_update.log"
MESSAGE_JSON_FILE="/tmp/message.json"

cd /data/www/SGDBackend-Nex2
. venv/bin/activate 

/usr/bin/touch $OUTPUT_FILE

python /data/www/SGDBackend-Nex2/scripts/loading/reference/reference_update_from_abc.py | /usr/bin/tee -a $OUTPUT_FILE
python /data/www/SGDBackend-Nex2/scripts/loading/reference/reference_display_name_update.py | /usr/bin/tee -a $OUTPUT_FILE
python /data/www/SGDBackend-Nex2/scripts/dumping/ncbi/dump_gene_pmid_pair.py | /usr/bin/tee -a $OUTPUT_FILE

cat $LOG_FILE >> $OUTPUT_FILE

/usr/bin/sed -i 's/$/\\n/' $OUTPUT_FILE

echo '{"Data": "From: '$(echo $EMAIL_FROM)'\nTo: '$(echo $EMAIL_TO)'\nSubject: data_dump.sh report\nMIME-Version: 1.0\nContent-type: Multipart/Mixed; boundary=\"NextPart\"\n\n--NextPart\nContent-Type: text/plain\n\ndata_dump.sh completed successfully\n\n--NextPart\nContent-Type: text/plain;\nContent-Disposition: attachment; filename=\"data_dump_report.txt\"\n\n'$(cat $OUTPUT_FILE)'\n--NextPart--"}' > $MESSAGE_JSON_FILE

/usr/local/bin/aws ses send-raw-email --cli-binary-format raw-in-base64-out --raw-message file://${MESSAGE_JSON_FILE}

exit 0
