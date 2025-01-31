from scripts.loading.database_session import get_session

nex_session = get_session()


rows = nex_session.execute("SELECT pmid FROM nex.referencedeleted").fetchall()

for x in rows:
    print("PMID:" + str(x[0]))

nex_session.close()

