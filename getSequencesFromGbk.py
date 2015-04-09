#! /usr/bin/python
"""
"""

from Bio import SeqIO, SeqRecord
from Bio.Seq import Seq
from Bio.Alphabet import IUPAC
from optparse import OptionParser
import sys, traceback

def main():
    usage = "usage: %prog [OPTIONS] GBK_FILE [GBK_FILE ...]"
    description = """
    Reads one or more sequence files from stdin or the argument list and outputs a list of sequences.
    """

# command line options
    parser = OptionParser(usage, description=description)
    parser.add_option("-o", "--outfile", dest="outfile",
                      metavar="OUTFILE", help="Write output sequences to OUTFILE.")
    parser.add_option("-f", "--formatIn", dest="formatIn", default="genbank",
        help="Input sequence format (see biopython docs)", metavar="FORMAT")
    parser.add_option("-F", "--formatOut", dest="formatOut", default="fasta",
        help="Output sequence format (see biopython docs)", metavar="FORMAT")
    parser.add_option("-c", "--codingSeq", dest="cds", default=False, action='store_true',
        help="Extract features of type CDS")
    parser.add_option("-t", "--translate",
                      default=False, action="store_true",
                      help="Translate output sequence to amino acids")
    parser.add_option("-r", "--refseq", default=False, action='store_true',
            help="If input is GBK and output is FASTA, make record id look \
            like a proper RefSeq entry: 'gi|XXX|ref|XXX'")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="Print status messages to stderr")
    parser.add_option("-A", "--about",
              action="store_true", dest="about", default=False,
              help="Print description")

    (options, args) = parser.parse_args()

    if options.about:
        print description
        exit(0)

    if options.verbose:
        global verbose
        verbose=True

    # output
    if options.outfile is None:
        log("Writting %s sequences to STDOUT" % (options.formatOut))
        outstream = sys.stdout
    else:
        log("Writting %s sequences to %s" % (options.formatOut, options.outfile))
        outstream = open(options.outfile,'w')

    if len(args)==0:
        log("reading sequences from STDIN")
        instream=sys.stdin
        translateStream(instream,options.formatIn,outstream, options.formatOut, options.cds, options.translate, options.refseq)
    else:
        for name in args:
            log("reading %s sequences from %s" % (options.formatIn, name))
            instream = open(name, 'rU')
            try:
                translateStream(instream,options.formatIn,outstream, options.formatOut, options.cds, options.translate, options.refseq)
            except:
                warn("Exception parsing %s:\n-----\n" % (name))
                traceback.print_exc(file=sys.stderr)
            instream.close()

#############
# Functions #
#############
verbose=False
def log(msg):
    if verbose:
        sys.stderr.write(msg)
        sys.stderr.write("\n")

def die( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()

def warn(msg):
    sys.stderr.write("WARNING: %s\n" % (msg))

def translateStream(instream, inf, outstream, outf, cds, translate, makeRefSeq):
    log("translating records from %s to %s (%s,%s)" % (inf,outf,cds,translate))
    records = SeqIO.parse(instream, inf)
    for record in records:
        if cds:
            # get coding sequences if requested
            translations = getCodingSequences(record, makeRefSeq)
        else:
            if makeRefSeq and 'gi' in record.annotations:
                record.id = "gi|%s|ref|%s|" % \
                (record.annotations['gi'],record.id)
            translations = (record,)

        if translations is None or len(translations)==0:
            warn("record %s has no features!" % (record.id))
            continue

        # change alphabet
        if translate:
            translations = [translateRecord(t) for t in translations]

        # write in new format
        for t in translations:
            log("writing %s" % (str(t)))
            SeqIO.write([t], outstream, outf)

def getCodingSequences(record, makeRefSeq):
    try:
        org = " [%s]" % (record.annotations['organism'])
    except:
        org=None

    seqs = []
    gene_count=0
    for f in record.features:
        if f.type == 'CDS':
            gene_count+=1
            if makeRefSeq:
                if 'protein_id' in f.qualifiers:
                    acc=f.qualifiers['protein_id'][0]
                else:
                    continue
                if 'db_xref' in f.qualifiers:
                    for ref in f.qualifiers['db_xref']:
                        if ref[0:2]=='GI':
                            gi=ref[3:]
                            break
                    else:
                        continue
                if 'translation' in f.qualifiers:
                    translation=f.qualifiers['translation'][0]
                else:
                    continue
                seq = Seq(translation, IUPAC.protein)
                r=SeqRecord.SeqRecord(seq,
                                      id="gi|%s|acc|%s|" % (gi,acc),
                                      name=acc)
            else:
                seq = f.extract(record.seq)
                r=SeqRecord.SeqRecord(seq)
                foundName=True
                if 'protein_id' in f.qualifiers:
                    r.id=f.qualifiers['protein_id'][0]
                    r.name=r.id
                elif 'db_xref' in f.qualifiers:
                    for ref in f.qualifiers['db_xref']:
                        if ref[0:2]=='GI':
                            r.id=ref
                            r.name=ref
                            break
                    else:
                        foundName=False
                else:
                    foundName=False

                if not foundName:
                    for q in ('locus_tag','name','id'):
                        if q in f.qualifiers:
                            r.id = f.qualifiers[q][0]
                            r.name=r.id
                            break
                    else:
                        #warn("No suitable name found for feature: %s" % (str(f.qualifiers)))
                        r.name='%s_GENE_%s' % (record.id,gene_count)
                        r.id=r.name

            desc = r.name
            for q in ('product','gene','note'):
                if q in f.qualifiers:
                    desc = f.qualifiers[q][0]
                    break

            if org is not None:
                desc+=org

            r.description=desc

            if 'db_xrefs' in f.qualifiers:
                r.dbxrefs=f.qualifiers['db_xrefs']

            log("created:\n%s\n from:\n%s" % (repr(r),repr(f)))
            seqs.append(r)

    return seqs

def translateRecord(record):
    record.seq = record.seq.translate()
    return record

if __name__ == '__main__':
    main()
