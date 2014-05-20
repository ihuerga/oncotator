import re
import logging

from oncotator.datasources.ChangeTransformingDatasource import ChangeTransformingDatasource
from oncotator.datasources.EnsemblTranscriptDatasource import EnsemblTranscriptDatasource
from oncotator.utils.VariantClassifier import VariantClassifier
from oncotator.TranscriptProviderUtils import TranscriptProviderUtils

AA_NAME_MAPPING = {
    'A': 'Ala',
    'R': 'Arg',
    'N': 'Asn',
    'D': 'Asp',
    'C': 'Cys',
    'E': 'Glu',
    'Q': 'Gln',
    'G': 'Gly',
    'H': 'His',
    'I': 'Ile',
    'L': 'Leu',
    'K': 'Lys',
    'M': 'Met',
    'F': 'Phe',
    'P': 'Pro',
    'S': 'Ser',
    'T': 'Thr',
    'W': 'Trp',
    'Y': 'Tyr',
    'V': 'Val',
    '*': '*',
}

COMPLEMENTARY_BASE_MAPPING = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A'}

PROT_REGEXP = re.compile('p\.([A-Z*])(\d+)([A-Z*])')

class HgvsChangeTransformingDatasource(ChangeTransformingDatasource):

    def __init__(self, src_file, title='', version=None):
        super(ChangeTransformingDatasource, self).__init__(src_file, title=title, version=version)
        self.output_headers = ['HGVS_genomic_change', 'HGVS_coding_DNA_change', 'HGVS_protein_change']

        self.vcer = VariantClassifier()

        #### HACK #####
        self.gencode_ds = EnsemblTranscriptDatasource(src_file)

        #### HACK #####
        ensembl_id_mapping_fname = '/Users/aramos/Desktop/ot_hgvs/ensembl_id_mappingsGRCh37.p13.txt'
        import pandas as pd
        self.ensembl_id_mapping = dict()
        with open(ensembl_id_mapping_fname) as in_fh:
            for line in in_fh:
                tx_id, prot_id = line.split('\t')[1:]
                self.ensembl_id_mapping[tx_id] = prot_id.replace('\n', '')
        
    def annotate_mutation(self, mutation):
        # TODO
        # TODO: When annotating, you should probably give the annotation a name like:  self.title + "_" + output_annotation_name
        # You can assume that the annotations from the transript datasource have already been populated (such as protein_change and genome_change)

#        if mutation['start'] in ['67969313', '67970596']:
#            from IPython import embed; embed()

        hgvs_genomic_change = self._adjust_genome_change(mutation)
        hgvs_coding_dna_change = self._adjust_coding_DNA_change(mutation)
        hgvs_protein_change = self._adjust_protein_change(mutation)

        mutation.createAnnotation('HGVS_genomic_change', hgvs_genomic_change, self.title)
        mutation.createAnnotation('HGVS_coding_DNA_change', hgvs_coding_dna_change, self.title)
        mutation.createAnnotation('HGVS_protein_change', hgvs_protein_change, self.title)

        return mutation

    def _adjust_genome_change(self, mutation):
        chrn = 'chr' + mutation['chr'] if not mutation['chr'].startswith('chr') else mutation['chr']
        change = '%d%s>%s' % (mutation['start'], mutation['ref_allele'], mutation['alt_allele'])
        if mutation['build'] == '':
            adjusted_genome_change = '%s:g.%s' % (chrn, change)
        else:
            adjusted_genome_change = '%s.%s:g.%s' % (chrn, mutation['build'], change)

        return adjusted_genome_change

    def _adjust_coding_DNA_change(self, mutation):
        vc = mutation['variant_classification']
        if vc in ['Intron', 'Splice_Site']:
            return self._get_cdna_change_for_intron(mutation)
        elif vc in ["5'UTR", 'De_novo_Start_OutOfFrame']:
            return self._get_cdna_change_for_5_utr(mutation)
        elif vc == "3'UTR":
            return self._get_cdna_change_for_3_utr(mutation)
        elif vc == 'IGR':
            return ''
        else:
            return '%s:%s' % (mutation['annotation_transcript'], mutation['transcript_change'])

    def _adjust_protein_change(self, mutation):
        if mutation['variant_classification'] in ['Intron', 'IGR', "3'UTR", "5'UTR", 'RNA',
            'lincRNA', 'Silent', 'Splice_Site', 'De_novo_Start_OutOfFrame']:
            return ''
        else:
            regx_res = PROT_REGEXP.match(mutation['protein_change'])
            ref_aa, aa_pos, alt_aa = [regx_res.group(i) for i in range(1, 4)]
            adjusted_prot_change = 'p.%s%s%s' % (AA_NAME_MAPPING[ref_aa], aa_pos, AA_NAME_MAPPING[alt_aa])
            prot_id = self._get_ensembl_prot_id_from_tx_id(mutation['annotation_transcript'])
            adjusted_prot_change = '%s:%s' % (prot_id, adjusted_prot_change)
            return adjusted_prot_change

    def _get_ensembl_prot_id_from_tx_id(self, tx_id):
        if '.' in tx_id:
            tx_id = tx_id[:tx_id.index('.')]
        return self.ensembl_id_mapping[tx_id]

    def _get_cdna_change_for_intron(self, mutation):
        #### HACK #####
        tx = self.gencode_ds.transcript_db[mutation['annotation_transcript']]
        nearest_exon = self.vcer._determine_closest_exon(tx, int(mutation['start']),
            int(mutation['end']))
        dist_to_exon = self.vcer._get_splice_site_coordinates(tx, int(mutation['start']),
            int(mutation['end']), nearest_exon)
        tx_exons = tx.get_exons()
    
        if dist_to_exon < 0 and mutation['transcript_strand'] == '+':
            cds_position_of_nearest_exon = TranscriptProviderUtils.convert_genomic_space_to_cds_space(
                tx_exons[nearest_exon][0], tx_exons[nearest_exon][0], tx)
            if mutation['variant_classification'] == 'Intron':
                #do not do for splice sites
                dist_to_exon = dist_to_exon - 1 #why substract 1? why only for positive strand transcript
        elif dist_to_exon < 0 and mutation['transcript_strand'] == '-':
            cds_position_of_nearest_exon = TranscriptProviderUtils.convert_genomic_space_to_cds_space(
                tx_exons[nearest_exon][1], tx_exons[nearest_exon][1], tx)
        elif dist_to_exon > 0 and mutation['transcript_strand'] == '+':
            cds_position_of_nearest_exon = TranscriptProviderUtils.convert_genomic_space_to_cds_space(
                tx_exons[nearest_exon][1], tx_exons[nearest_exon][1], tx)
        elif dist_to_exon > 0 and mutation['transcript_strand'] == '-':
            cds_position_of_nearest_exon = TranscriptProviderUtils.convert_genomic_space_to_cds_space(
                tx_exons[nearest_exon][0], tx_exons[nearest_exon][0], tx)

        if cds_position_of_nearest_exon[0] == 0:
            #this means intron occurs before start codon and thus cds position needs to be adjusted to a negative number
            exon_coords = TranscriptProviderUtils.convert_genomic_space_to_exon_space(mutation['start'],
                tx.determine_cds_start() + 1, tx)
            cds_position_of_nearest_exon = exon_coords[0] - exon_coords[1]
        else:
            cds_position_of_nearest_exon = cds_position_of_nearest_exon[0]

        if dist_to_exon < 0:   
            cds_position_of_nearest_exon += 1 #why add 1?

#        if mutation['start'] == 80529551:
#            from IPython import embed; embed()
        
        sign = '-' if dist_to_exon < 0 else '+'
        dist_to_exon = abs(dist_to_exon)

        tx_ref_allele, tx_alt_allele = self._get_tx_alleles(mutation)

        adjusted_tx_change = 'c.%d%s%d%s>%s' % (cds_position_of_nearest_exon, sign, dist_to_exon,
            tx_ref_allele, tx_alt_allele)

        return '%s:%s' % (mutation['annotation_transcript'], adjusted_tx_change)


#TranscriptProviderUtils.convert_genomic_space_to_cds_space(80529551, 80529551, tx)
#TranscriptProviderUtils.convert_genomic_space_to_cds_space(tx_exons[nearest_exon][0], tx_exons[nearest_exon][0], tx)
#self.vcer._get_splice_site_coordinates(tx, 484634, 484634, nearest_exon)
#self.vcer._get_splice_site_coordinates(tx, 484814, 484814, nearest_exon)

    def _get_cdna_change_for_5_utr(self, mutation):
        #### HACK #####
        tx = self.gencode_ds.transcript_db[mutation['annotation_transcript']]
        dist_from_cds_start = abs(mutation['start'] - tx.determine_cds_start())
        tx_ref_allele, tx_alt_allele = self._get_tx_alleles(mutation)
        adjusted_tx_change = 'c.-%d%s>%s' % (dist_from_cds_start, tx_ref_allele, tx_alt_allele)
        return '%s:%s' % (mutation['annotation_transcript'], adjusted_tx_change)

    def _get_cdna_change_for_3_utr(self, mutation):
        #### HACK #####
        tx = self.gencode_ds.transcript_db[mutation['annotation_transcript']]
        dist_from_cds_stop = abs(mutation['start'] - tx.determine_cds_stop() + 2)
        tx_ref_allele, tx_alt_allele = self._get_tx_alleles(mutation)
        adjusted_tx_change = 'c.*%d%s>%s' % (dist_from_cds_stop, tx_ref_allele, tx_alt_allele)
        return '%s:%s' % (mutation['annotation_transcript'], adjusted_tx_change)

    def _get_tx_alleles(self, mutation):
        tx_ref_allele, tx_alt_allele = mutation['ref_allele'], mutation['alt_allele']
        if mutation['transcript_strand'] == '-':
            tx_ref_allele, tx_alt_allele = COMPLEMENTARY_BASE_MAPPING[tx_ref_allele], COMPLEMENTARY_BASE_MAPPING[tx_alt_allele]
        return tx_ref_allele, tx_alt_allele

