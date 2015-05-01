import subprocess, logging, re, os, glob
logger = logging.getLogger(__name__)

class TMOptions():
    def getBaseCommand(self):
        baseCommand = ['java', '-classpath', self.jarPath]
        return baseCommand

    def findJar(self, jarPath):
        if jarPath is not None:
            return jarPath

        # jar is in edl dir
        edlLib = os.path.dirname(os.path.abspath(__file__))
        return glob.glob(os.path.sep.join([edlLib,'trimmomatic.jar']))[0]
        
    def runTmatic(self):
        command=self.buildCommand()
        logger.info("Running Trimmomatic")
        logger.debug("Tmatic command:\n%s" % (command))
        p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True)
        (stdout,stderr)=p.communicate()
        self.stdout=stdout
        self.stderr=stderr
        self.exitcode=p.returncode
        logger.debug("scanning output")
        self.getCountsFromLog()

class TMOptionsPE(TMOptions):
    javaclass='org.usadellab.trimmomatic.TrimmomaticPE'
    def __init__(self,forward,reverse,jarPath=None,primers=None,pref=None,primerSettings=None):
        self.forward=forward
        self.reverse=reverse
        self.outpref=pref
        self.primers=primers
        self.setOutfiles()
        self.primerSettings=primerSettings
        self.jarPath = self.findJar(jarPath)

    def setOutfiles(self):
        self.outfiles={}
        if self.outpref is not None:
            base="%s/tmatic" % (self.outpref)
            for suff in ['1u','1p','2u','2p']:
                self.outfiles[suff]="%s.%s" % (base,suff)
        else:
            self.outfiles['1u']="%s.tm.u" %(self.forward)
            self.outfiles['1p']="%s.tm.p" %(self.forward)
            self.outfiles['2u']="%s.tm.u" %(self.reverse)
            self.outfiles['2p']="%s.tm.p" %(self.reverse)

    def buildCommand(self):
        command=" ".join(self.getBaseCommand())
        command+=" " + self.javaclass
        if logging.getLogger().level<=logging.DEBUG:
            command+=" -trimlog %s.log" % self.outfiles['1p']
        command='%s "%s"' % (command,self.forward)
        command='%s "%s"' % (command,self.reverse)
        command='%s "%s"' % (command, self.outfiles['1p'])
        command='%s "%s"' % (command, self.outfiles['1u'])
        command='%s "%s"' % (command, self.outfiles['2p'])
        command='%s "%s"' % (command, self.outfiles['2u'])
        if self.primers is not None:
            if self.primerSettings is None:
                clippingVals="2:40:15"
            else:
                clippingVals=self.primerSettings

            command += " ILLUMINACLIP:%s:%s" % (self.primers,clippingVals)
        return command

    def getCountsFromLog(self):
        """
        parses STDERR string for line listing read counts:

        Input Read Pairs: 23132462 Both Surviving: 23008441 (99.46%) Forward Only Surviving: 124005 (0.54%) Reverse Only Surviving: 0 (0.00%) Dropped: 16 (0.00%)
        """
        match=re.search(r'Input Read Pairs:\s*(\d+)\s+Both Surviving:\s*(\d+)\s+.+Dropped:\s*(\d+)\b', self.stderr)
        if match:
            (processed, passed, dropped) = match.groups()
            self.counts={'processed':processed,
                         'passed':passed,
                         'dropped':dropped}
        else:
            logger.warn("Cannot parse counts from Trimmomatic log!")
            self.counts=None

class TMOptionsSE(TMOptions):
    javaclass='org.usadellab.trimmomatic.Trimmomatic'
    def __init__(self,input,output,jarPath=None,endQuality=5,minLength=45):
        self.input=input
        self.output=output
        self.endQuality=endQuality
        self.minLength=minLength
        self.jarPath = self.findJar(jarPath)

    def buildCommand(self):
        command=" ".join(self.getBaseCommand())
        command+=" " + self.javaclass
        command = '%s "%s"' %  (command, self.input)
        command='%s "%s"' %  (command, self.output)
        if self.endQuality>0:
            command+= " " + "LEADING:%d" % (self.endQuality)
            command+= " " + "TRAILING:%d" % (self.endQuality)
        if self.minLength>0:
            command+= " " + "MINLEN:%d" % (self.minLength)
        return command

    def getCountsFromLog(self):
        """
        parses STDERR string for line listing read counts:

        Input Reads: 1517888 Surviving: 0 (0.00%) Dropped: 1517888 (100.00%)
        """
        match=re.search(r'Input Reads:\s*(\d+)\s+Surviving:\s*(\d+)\s+.+Dropped:\s*(\d+)\b', self.stderr)
        if match:
            (processed, passed, dropped) = match.groups()
            self.counts={'processed':processed,
                         'passed':passed,
                         'dropped':dropped}
        else:
            logger.warn("Cannot parse counts from Trimmomatic log!")
            self.counts=None
        passmatch=re.search(r'Input Read Pairs: ')
