import os
import redis

disambiguation_table = redis.Redis(os.environ['REDIS_WTITE_HOST'], os.environ['REDIS_PORT'])


# dbid = disambiguation_table.get(("/" + prefix + "/" + id).upper())
dbid = disambiguation_table.get("/locus/ACT1")

print ("dbid for ACT1 is", dbid)

dbid = disambiguation_table.get("/chemical/CHEBI:132369")

print ("dbid for CHEBI:132369 is", dbid)

dbid = disambiguation_table.get("/chemical/CHEBI:17234")

print ("dbid for CHEBI:17234 is", dbid)
