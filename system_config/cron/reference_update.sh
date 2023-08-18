#!/bin/sh

OUTPUT_FILE=/tmp/output.log            # output written here
OUTPUT2_FILE=/tmp/output2.log          # processed output to be included in JSON email message
MESSAGE_JSON_FILE=/tmp/message.json    # pre-processed JSON email message
MESSAGE2_JSON_FILE=/tmp/message2.json  # post-processed JSON email message

cd /data/www/SGDBackend-Nex2
. venv/bin/activate 

echo "reference_update.sh start:  `/bin/date`" | /bin/tee $OUTPUT_FILE

# set credentials to access ABC
export AWS_ACCESS_KEY_ID=$ABC_AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=$ABC_AWS_SECRET_ACCESS_KEY

/usr/bin/cp /dev/null $LOG_FILE
python /data/www/SGDBackend-Nex2/scripts/loading/reference/reference_update_from_abc.py 2>&1 | /usr/bin/tee -a $OUTPUT_FILE
grep -v '_abstract=' $LOG_FILE >> $OUTPUT_FILE

# use IAM for further permissions rather than access keys
unset AWS_ACCESS_KEY_ID
unset AWS_SECRET_ACCESS_KEY

/usr/bin/cp /dev/null $LOG_FILE
python /data/www/SGDBackend-Nex2/scripts/loading/reference/reference_display_name_update.py 2>&1 | /usr/bin/tee -a $OUTPUT_FILE
cat $LOG_FILE >> $OUTPUT_FILE

/usr/bin/cp /dev/null $LOG_FILE
python /data/www/SGDBackend-Nex2/scripts/dumping/ncbi/dump_gene_pmid_pair.py 2>&1 | /usr/bin/tee -a $OUTPUT_FILE
cat $LOG_FILE >> $OUTPUT_FILE

echo "reference_update.sh finished:  `/bin/date`" | /bin/tee -a $OUTPUT_FILE

# add \n characters to end of each line in OUTPUT_FILE for JSON message
/usr/bin/touch $OUTPUT2_FILE
/usr/bin/awk '{printf "%s\\n", $0}' $OUTPUT_FILE > $OUTPUT2_FILE

# create JSON email message
echo '{"Data": "From: '$(echo $EMAIL_FROM)'\nTo: '$(echo $EMAIL_TO)'\nSubject: reference_update.sh report\nMIME-Version: 1.0\nContent-type: Multipart/Mixed; boundary=\"NextPart\"\n\n--NextPart\nContent-Type: text/plain\n\nreference_update.sh completed successfully\n\n--NextPart\nContent-Type: text/plain;\nContent-Disposition: attachment; filename=\"reference_update_report.txt\"\n\n'$(cat $OUTPUT2_FILE)'\n--NextPart--"}' > $MESSAGE_JSON_FILE

# replace literal newline characters with literal '\n' characters in JSON message
/usr/bin/sed -i 's/$/\\n/' $MESSAGE_JSON_FILE
/usr/bin/touch $MESSAGE2_JSON_FILE
/usr/bin/tr -d '\n' < $MESSAGE_JSON_FILE > $MESSAGE2_JSON_FILE
/usr/bin/sed -i 's/}\\n/}\n/' $MESSAGE2_JSON_FILE  # add final trailing newline

/usr/local/bin/aws ses send-raw-email --cli-binary-format raw-in-base64-out --raw-message file://${MESSAGE2_JSON_FILE} --region $AWS_SES_REGION

exit $?
