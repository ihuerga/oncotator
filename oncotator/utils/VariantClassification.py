
class VariantClassification(object):
    """ Stores the names and values of a variant classification.
    """
    INTRON = "Intron"
    FIVE_PRIME_UTR = "5'UTR"
    THREE_PRIME_UTR = "3'UTR"
    IGR = "IGR"
    FIVE_PRIME_PRIME_FLANK = "5'Flank"
    THREE_PRIME_PRIME_FLANK = "3'Flank"
    MISSENSE = "Missense_Mutation"
    NONSENSE = "Nonsense_Mutation"
    SILENT = "Silent"
    SPLICE_SITE = "Splice_Site"
    IN_FRAME_DEL = "In_Frame_Del"
    IN_FRAME_INS = "In_Frame_Ins"
    FRAME_SHIFT_INS = "Frame_Shift_Ins"
    FRAME_SHIFT_DEL = "Frame_Shift_Del"
    START_CODON_INS = "Start_Codon_Ins"
    START_CODON_DEL = "Start_Codon_Del"
    STOP_CODON_INS = "Stop_Codon_Ins"
    STOP_CODON_DEL = "Stop_Codon_Del"
    DE_NOVO_START = "De_novo_Start"

    VT_INS = "INS"
    VT_DEL = "DEL"

    def __init__(self):
        self._vc_primary = ""
        self._vc_secondary = ""
        self._transcript_id = ""
        self._mut_codon = ""
        self._ref_aa = ""
        self._ref_protein_start = ""
        self._ref_protein_end = ""
        self._alt_aa = ""
        self._alt_protein_start = ""
        self._alt_protein_end = ""

