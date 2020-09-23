import sys
from src.models import LocusAlias, Referencedbentity
from scripts.loading.database_session import get_session

__author__ = 'sweng66'
 
protein_file = "scripts/dumping/linkout/data/ProteinResource.xml"
ref_file = "scripts/dumping/linkout/data/RefResource.xml"

def dump_data():
 
    nex_session = get_session()

    ## protein resources
    
    fw = open(protein_file, "w")
    write_protein_resource_head(fw)    
    for x in nex_session.query(LocusAlias).filter_by(alias_type='RefSeq protein version ID').all():
        display_name = x.display_name.split('.')[0]
        fw.write("            <Query>" + display_name + " [pacc]</Query>\n")
    write_protein_resource_end(fw)
    fw.close()

    ## ref resources
    
    fw = open(ref_file, "w")
    write_ref_resource_head(fw)
    for x in nex_session.query(Referencedbentity).all():
        if x.pmid:
            fw.write("            <ObjId>" + str(x.pmid) + "</ObjId>\n")
    write_ref_resource_end(fw)
    fw.close()


def write_protein_resource_head(fw):

    fw.write('<!DOCTYPE LinkSet PUBLIC "-//NLM//DTD LinkOut 1.0//EN" "LinkOut.dtd"' + "\n") 
    fw.write('[ <!ENTITY icon.url  "https://d1x6jdqbvd5dr.cloudfront.net/legacy_img/SGD-t.gif">' + "\n") 
    fw.write('<!ENTITY base.url  "https://www.yeastgenome.org/search?is_quick=true&q=">]>' + "\n")
    fw.write("<LinkSet>\n\n") 
    fw.write("    <Link>\n") 
    fw.write("    <LinkId>1</LinkId>\n") 
    fw.write("    <ProviderId>3471</ProviderId>\n") 
    fw.write("    <IconUrl>&icon.url;</IconUrl>\n") 
    fw.write("    <ObjectSelector>\n") 
    fw.write("        <Database>Protein</Database>\n") 
    fw.write("        <ObjectList>\n") 

def write_protein_resource_end(fw):

    fw.write("        </ObjectList>\n")
    fw.write("    </ObjectSelector>\n")
    fw.write("    <ObjectUrl>\n")
    fw.write("        <Base>&base.url;</Base>\n")
    fw.write("        <Rule>q=&lo.pacc;</Rule>\n")
    fw.write("    </ObjectUrl>\n") 
    fw.write("    </Link>\n") 
    fw.write("</LinkSet>\n") 

def write_ref_resource_head(fw):

    fw.write('<!DOCTYPE LinkSet PUBLIC "-//NLM//DTD LinkOut 1.0//EN" "LinkOut.dtd"' + "\n")
    fw.write('[ <!ENTITY icon.url "https://d1x6jdqbvd5dr.cloudfront.net/legacy_img/SGD-t.gif">' + "\n") 
    fw.write('<!ENTITY base.url "https://www.yeastgenome.org/reference/">]>' + "\n") 
    fw.write("<LinkSet>\n\n") 
    fw.write("    <Link>\n") 
    fw.write("    <LinkId>1</LinkId>\n") 
    fw.write("    <ProviderId>3471</ProviderId>\n") 
    fw.write("    <IconUrl>&icon.url;</IconUrl>\n") 
    fw.write("    <ObjectSelector>\n") 
    fw.write("        <Database>PubMed</Database>\n") 
    fw.write("        <ObjectList>\n") 

def write_ref_resource_end(fw):

    fw.write("        </ObjectList>\n") 
    fw.write("    </ObjectSelector>\n") 
    fw.write("    <ObjectUrl>\n") 
    fw.write("        <Base>&base.url;</Base>\n")
    fw.write("        <Rule>&lo.id;</Rule>\n")
    fw.write("    </ObjectUrl>\n") 
    fw.write("    </Link>\n")
    fw.write("</LinkSet>\n")
    
if __name__ == '__main__':
    
    dump_data()

    


