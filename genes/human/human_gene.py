#!usr/bin/env python
# -*- coding: utf-8 -*-

'''
Authors: 
  Andra Waagmeester (andra' at ' micelio.be)

This file is part of ProteinBoxBot.

ProteinBoxBot is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

ProteinBoxBot is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with ProteinBoxBot.  If not, see <http://www.gnu.org/licenses/>.
'''

__author__ = 'Andra Waagmeester'
__license__ = 'GPL'

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../ProteinBoxBot_Core")
import PBB_Core
import PBB_Debug
import PBB_login
import PBB_settings
import PBB_Functions
import ProteinBoxBotKnowledge
import urllib
import urllib3
import certifi
import copy

import sys
import mygene_info_settings

try:
    import simplejson as json
except ImportError as e:
    import json
    
"""
This is the human-genome specific part of the ProteinBoxBot. Its purpose is to enrich Wikidata with
human gene and known external identifiers.
  
"""
    
class human_genome():
    def __init__(self):
        counter = 0
        self.content = json.loads(self.download_human_genes())
        self.gene_count = self.content["total"]
        self.genes = self.content["hits"]
        self.logincreds = PBB_login.WDLogin(PBB_settings.getWikiDataUser(), PBB_settings.getWikiDataPassword())
        
        entrezWikidataIds = dict()
        print "Getting all entrez genes in Wikidata"
        InWikiData = PBB_Core.WDItemList("CLAIM[703:5] AND CLAIM[351]", "351")
        for geneItem in InWikiData.wditems["props"]["351"]:
            entrezWikidataIds[str(geneItem[2])] = geneItem[0]
            
        for gene in self.genes:
            if str(gene["entrezgene"]) in entrezWikidataIds.keys():
               gene["wdid"] = 'Q'+str(entrezWikidataIds[str(gene["entrezgene"])])
            else:
               gene["wdid"] = None 
            gene["logincreds"] = self.logincreds
            geneClass = human_gene(gene)
            if str(geneClass.entrezgene) in entrezWikidataIds.keys():
                geneClass.wdid = 'Q'+str(entrezWikidataIds[str(geneClass.entrezgene)])
                print geneClass.wdid
            else: 
                geneClass.wdid = None 
            if geneClass.wdid != None:
                print geneClass.wdid + " will be updated as Entrez "+ str(geneClass.entrezgene)
                PBB_Debug.prettyPrint(geneClass.wd_json_representation)
                print "adding "+str(geneClass.entrezgene) + " as statement" 
                counter = counter +1
                if counter == 100:
                   sys.exit()
            else:
                print str(geneClass.entrezgene) + " needs to be added to Wikidata"

    def download_human_genes(self):
        """
        Downloads the latest list of human genes from mygene.info through the URL specified in mygene_info_settings
        """
        # request = urllib2.Request(mygene_info_settings.getHumanGenesUrl())
        urllib.urlretrieve (mygene_info_settings.getHumanGenesUrl(), "human_genes.json")
        file = open("human_genes.json", 'r')
        return file.read()
        
class human_gene(object):
    def __init__(self, object):
        self.content = object
        self.entrezgene = object["entrezgene"]
        self.name = object["name"]
        self.logincreds = object["logincreds"]
        gene_annotations = json.loads(self.annotate_gene())
        print "gene_annotations"
        PBB_Debug.prettyPrint(gene_annotations)
        print "object"
        PBB_Debug.prettyPrint(object)
        self.annotationstimestamp = gene_annotations["_timestamp"]
        self.wdid = object["wdid"]
        
        # symbol
        if isinstance(gene_annotations["symbol"], list):
             self.symbol = object["symbol"]
        else:
             self.symbol = [object["symbol"]]
        
        # HGNC
        if "HGNC" in gene_annotations:
            if isinstance(gene_annotations["HGNC"], list): 
                self.hgnc = gene_annotations["HGNC"]
            else:
                self.hgnc = [gene_annotations["HGNC"]]
        else:
            self.hgnc = None
            
        # Ensembl Gene & transcript
        if "ensembl" in gene_annotations:
            if "gene" in gene_annotations["ensembl"]:
                if isinstance(gene_annotations["ensembl"]["gene"], list): 
                    self.ensembl_gene = gene_annotations["ensembl"]["gene"]
                else:
                    self.ensembl_gene = [gene_annotations["ensembl"]["gene"]]
            else:
                self.ensembl_gene = None
            
            if "transcript" in gene_annotations["ensembl"]:
                if isinstance(gene_annotations["ensembl"]["transcript"], list): 
                    self.ensembl_transcript = gene_annotations["ensembl"]["transcript"]
                else:
                    self.ensembl_transcript = [gene_annotations["ensembl"]["transcript"]]
            else:
                self.ensembl_transcript = None
        # Homologene
        if "homologene" in gene_annotations:
            if isinstance(gene_annotations["homologene"]["id"], list): 
                self.homologene = gene_annotations["homologene"]["id"]
            else:
                self.homologene = [gene_annotations["homologene"]["id"]]
        else:
            self.homologene = None
        # Refseq 
        if "refseq" in gene_annotations:
            if "rna" in gene_annotations["refseq"]:
                if isinstance(gene_annotations["refseq"]["rna"], list): 
                    self.refseq_rna = gene_annotations["refseq"]["rna"]
                else:
                    self.refseq_rna = [gene_annotations["refseq"]["rna"]]
            else :
                self.refseq_rna = None
        else :
            self.refseq_rna = None       
        if "genomic_pos" in gene_annotations:
            self.genomic_pos =[]
            if (isinstance(gene_annotations["genomic_pos"], list)):
                for i in range(len(gene_annotations["genomic_pos"])):
                    self.genomic_pos.append(ProteinBoxBotKnowledge.chromosomes[gene_annotations["genomic_pos"][i]["chr"]])

            if isinstance(gene_annotations["genomic_pos"], list): 
                self.genomic_pos = gene_annotations["genomic_pos"]

            else:
                self.genomic_pos = [gene_annotations["genomic_pos"]]
        else:
            self.genomic_pos = None
        
        # type of Gene
        if "type_of_gene" in gene_annotations:
            self.type_of_gene = []
            if gene_annotations["type_of_gene"]=="ncRNA":
                self.type_of_gene.append("Q427087")
        else:
            self.type_of_gene = None
        # Reference section           
        gene_reference = {
                    'ref_properties': [u'P248', u'P143', 'TIMESTAMP'],
                    'ref_values': [u'Q17939676', u'Q20641742' , 'TIMESTAMP']
                }
                   
        references = dict()
        

        data2add = dict()
        data2add["P279"] = ["7187"]
        references['P279'] = [copy.deepcopy(gene_reference)]
        data2add["P703"] = ["5"]
        references['P703'] = [copy.deepcopy(gene_reference)]    
        data2add['P351'] = [str(self.entrezgene)]
        references['P351'] = [copy.deepcopy(gene_reference)]
        data2add['P353'] = self.symbol
        references['P353'] = [copy.deepcopy(gene_reference)]
        # references['P353'] = gene_reference
        
        '''if "type_of_gene" in vars["self"]:
            if self.type_of_gene != None:
                data2add["P279"]
                '''
        
        if "ensembl_gene" in vars(self):
            if self.ensembl_gene != None:
                data2add["P594"] = self.ensembl_gene
                references['P594'] = []
                for i in range(len(self.ensembl_gene)):
                    references['P594'].append(copy.deepcopy(gene_reference))
        if "ensembl_transcript" in vars(self):
            if self.ensembl_transcript != None:
                data2add['P704'] = self.ensembl_transcript
                references['P704'] = []
                for i in range(len(self.ensembl_transcript)):
                    references['P704'].append(copy.deepcopy(gene_reference))
        if "hgnc" in vars(self):
            if self.hgnc != None:
                data2add['P354'] = self.hgnc
                references['P354'] = []
                for i in range(len(self.hgnc)):
                    references['P354'].append(copy.deepcopy(gene_reference))
        if "homologene" in vars(self):
            if self.homologene != None:
                data2add['P593'] = self.homologene
                references['P593'] = []
                for i in range(len(self.homologene)):
                    references['P593'].append(copy.deepcopy(gene_reference))
        if "refseq_rna" in vars(self):
            if self.refseq_rna != None:
                data2add['P639'] = self.refseq_rna
                references['P639'] = []
                for i in range(len(self.refseq_rna)):
                    references['P639'].append(copy.deepcopy(gene_reference))
                else:
                    data2add['P639'] = []
                    references['P639'] = []
        if "genomic_pos" in object:
            if (isinstance(object["genomic_pos"], list)):
               chromosome = object["genomic_pos"][0]["chr"]
            else: chromosome = object["genomic_pos"]["chr"]
            data2add['P1057'] =  chromosomes[str(chromosome)]
            references['P1057'] = gene_reference    


        if "alias" in gene_annotations.keys(): 
            self.synonyms = gene_annotations["alias"]
        else:
            self.synonyms = None
        if self.wdid != None: 
            PBB_Debug.prettyPrint(vars(self)) 
            PBB_Debug.prettyPrint(data2add) 
            PBB_Debug.prettyPrint(references) 
  
            wdPage = PBB_Core.WDItemEngine(self.wdid, self.name, data = data2add, server="www.wikidata.org", references=references)
            print self.wdid
            self.wd_json_representation = wdPage.get_wd_json_representation() 
            wdPage.write(self.logincreds)
            #PBB_Debug.prettyPrint(self.wd_json_representation)
            #sys.exit()
        print "References: "
        print references
               
    def annotate_gene(self):
        "Get gene annotations from mygene.info"
        http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
        request = http.request("GET", mygene_info_settings.getGeneAnnotationsURL()+str(self.entrezgene))
        return request.data
        
        
 
        
        
        
        
        