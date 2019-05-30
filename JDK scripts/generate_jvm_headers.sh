# Headers that are generated using instructions from:
# jdk8/hotspot/make/linux/makefiles/jvmti.make
#                                   adlc.make
#                                   trace.make
#                                   rules.make

######################################################
# jvmti:                                             #
######################################################

JvmtiSrcDir="../../jdk8/hotspot/src/share/vm/prims/"
InterpreterSrcDir="../../jdk8/hotspot/src/share/vm/interpreter"
JvmtiOutDir="./jvmtifiles/"

mkdir -p jvmtifiles

javac -d $JvmtiOutDir $JvmtiSrcDir/jvmtiGen.java
javac -d $JvmtiOutDir $JvmtiSrcDir/jvmtiEnvFill.java

XSLT="java -classpath $JvmtiOutDir jvmtiGen"

# JvmtiEnter.cpp
$XSLT -IN $JvmtiSrcDir/jvmti.xml -XSL $JvmtiSrcDir/jvmtiEnter.xsl -OUT $JvmtiOutDir/jvmtiEnter.cpp -PARAM interface jvmti

# bytecodeInterpreterWithChecks.cpp
$XSLT -IN $InterpreterSrcDir/bytecodeInterpreterWithChecks.xml -XSL $InterpreterSrcDir/bytecodeInterpreterWithChecks.xsl -OUT $JvmtiOutDir/bytecodeInterpreterWithChecks.cpp 

# jvmtiEnterTrace.cpp
$XSLT -IN $JvmtiSrcDir/jvmti.xml -XSL $JvmtiSrcDir/jvmtiEnter.xsl -OUT $JvmtiOutDir/jvmtiEnterTrace.cpp -PARAM interface jvmti -PARAM trace Trace

# jvmtiEnvRecommended.cpp
$XSLT -IN $JvmtiSrcDir/jvmti.xml -XSL $JvmtiSrcDir/jvmtiEnv.xsl -OUT $JvmtiOutDir/jvmtiEnvStub.cpp
java -classpath $JvmtiOutDir jvmtiEnvFill $JvmtiSrcDir/jvmtiEnv.cpp $JvmtiOutDir/jvmtiEnvStub.cpp $JvmtiOutDir/jvmtiEnvRecommended.cpp

# jvmtiEnv.hpp
$XSLT -IN $JvmtiSrcDir/jvmti.xml -XSL $JvmtiSrcDir/jvmtiHpp.xsl -OUT $JvmtiOutDir/jvmtiEnv.hpp

# jvmti.h
$XSLT -IN $JvmtiSrcDir/jvmti.xml -XSL $JvmtiSrcDir/jvmtiH.xsl -OUT $JvmtiOutDir/jvmti.h


######################################################
# trace:                                             #
######################################################

TraceOutDir="./tracefiles"
TraceSrcDir="../../jdk8/hotspot/src/share/vm/trace"

mkdir -p $TraceOutDir

# GENERATE_CODE= \
#   $(QUIETLY) echo Generating $@; \
#   $(XSLT) -IN $(word 1,$^) -XSL $(word 2,$^) -OUT $@; \
#   test -f $@

# $XSLT -IN $(word 1,$^) -XSL $(word 2,$^) -OUT $@; \
# test -f $@

# $(TraceOutDir)/traceEventIds.hpp: $(TraceSrcDir)/trace.xml $(TraceSrcDir)/traceEventIds.xsl $(XML_DEPS)
# 	$(GENERATE_CODE)

$XSLT -IN $TraceSrcDir/trace.xml -XSL $TraceSrcDir/traceEventIds.xsl -OUT $TraceOutDir/traceEventIds.hpp;
test -f $TraceOutDir/traceEventIds.hpp

# $(TraceOutDir)/traceTypes.hpp: $(TraceSrcDir)/trace.xml $(TraceSrcDir)/traceTypes.xsl $(XML_DEPS)
# 	$(GENERATE_CODE)

$XSLT -IN $TraceSrcDir/trace.xml -XSL $TraceSrcDir/traceTypes.xsl -OUT $TraceOutDir/traceTypes.hpp; \
test -f $TraceOutDir/traceTypes.hpp

# $(TraceOutDir)/traceEventClasses.hpp: $(TraceSrcDir)/trace.xml $(TraceSrcDir)/traceEventClasses.xsl $(XML_DEPS)
# 	$(GENERATE_CODE)

$XSLT -IN $TraceSrcDir/trace.xml -XSL $TraceSrcDir/traceEventClasses.xsl -OUT $TraceOutDir/traceEventClasses.hpp; \
test -f $TraceOutDir/traceEventClasses.hpp
