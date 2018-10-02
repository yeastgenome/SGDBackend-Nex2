# dev
export DEV_SERVER="www5.dev.yeastgenome.org"
#export DEV_SERVER="www3.dev.yeastgenome.org"
# curate-dev
export CURATE_DEV_SERVER="curate1.qa.yeastgenome.org"
export PREVIEW_SERVER="preview1.qa.yeastgenome.org"
export CURATE_NEX2_URI="postgresql://otto:db4auto@db-curate.qa.yeastgenome.org:5432/sgd"
# qa
export QA_SERVER="www1.qa.yeastgenome.org"
#delete
export QA_NEX2_URI="postgresql://otto:db4auto@db-curate.qa.yeastgenome.org:5432/sgd"
#export QA_NEX2_URI="postgresql://otto:db4auto@db-master.qa.yeastgenome.org:5432/sgd"
# use curate db
#export NEX2_URI="postgresql://otto:db4auto@db-curate.qa.yeastgenome.org:5432/sgd"
export NEX2_URI="postgresql://otto:db4auto@db-master.qa.yeastgenome.org:5432/sgd" #main guy
# export NEX2_URI="postgresql://otto:db4auto@db-master.dev.yeastgenome.org:5432/sgd"
# export Test_NEX2_URI="postgresql://otto:db4auto@db-master.dev.yeastgenome.org:5432/sgd"
# export NEX2_DEV_MASTER_URI="postgresql://otto:db4auto@db-master.dev.yeastgenome.org:5432/sgd"
#export NEX2_URI="postgresql://localhost:5432/sgd"
export BATTER_URI="http://batter.stanford.edu/cgi-bin/termfinder2.pl"
# misc curation stuff
export S3_ACCESS_KEY="AKIAI67QFBAFDEXF74YQ"
export S3_SECRET_KEY="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"
export S3_BUCKET="sgd-dev-upload"

export DEFAULT_USER="otto"
export GOOGLE_CLIENT_ID="333079536508-2kluhsd2krnnq9v9pq4j6i107iurp6ms.apps.googleusercontent.com"
export GOOGLE_CAPTCHA_ID="6Ldz_hgUAAAAADHgAB3itoKPBFqnspuHX1vdCuEg"
export GOOGLE_CAPTCHA_SECRET="6Ldz_hgUAAAAAEINGGhioTi92A4O4zCk7B7KSlf3"
export PUSHER_APP_ID="315431"
export PUSHER_KEY="6b78e7b7de8ae3709235"
export PUSHER_SECRET="52726d5db142ca77be02"
export CACHE_URLS="http://preview1.qa.yeastgenome.org"
# ES stuff
export WRITE_ES_URI="http://es-2a.yeastgenome.org:9200/"
export ES_URI="http://es-2a.yeastgenome.org:9200/"
#export ES_URI="http://sgd-elasticsearch-cluster-361056584.us-west-2.elb.amazonaws.com/"

# TEMP local
#export WRITE_ES_URI="http://localhost:9200/"
#export ES_URI="http://localhost:9200/"

export ES_INDEX_NAME='searchable_items_dev'
#export ES_INDEX_NAME='searchable_items_test'

#local stuff
export LOCAL_FILE_DIRECTORY=''
# aws s3 cp archive-file.tar.gz s3://mod-datadumps/
