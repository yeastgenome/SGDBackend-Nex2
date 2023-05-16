#!/bin/sh

OUTPUT_FILE=${LOG_FILE}
MESSAGE_JSON_FILE="/tmp/message.json"

echo "data_dump.sh start:  `/bin/date`" | /bin/tee $OUTPUT_FILE

cd /data/www/SGDBackend-Nex2
. venv/bin/activate && \
    python scripts/dumping/curation/dump_gff.py | /bin/tee -a $OUTPUT_FILE

echo "data_dump.sh end:  `/bin/date`" | /bin/tee -a $OUTPUT_FILE

/usr/bin/sed -i 's/$/\\n/' $OUTPUT_FILE

echo '{"Data": "From: '$(echo $EMAIL_FROM)'\nTo: '$(echo $EMAIL_TO)'\nSubject: data_dump.sh report\nMIME-Version: 1.0\nContent-type: Multipart/Mixed; boundary=\"NextPart\"\n\n--NextPart\nContent-Type: text/plain\n\ndata_dump.sh completed successfully\n\n--NextPart\nContent-Type: text/plain;\nContent-Disposition: attachment; filename=\"data_dump_report.txt\"\n\n'$(cat $OUTPUT_FILE)'\n--NextPart--"}' > $MESSAGE_JSON_FILE

/usr/local/bin/aws ses send-raw-email --cli-binary-format raw-in-base64-out --raw-message file://${MESSAGE_JSON_FILE}
