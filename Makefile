# File: Makefile
# By: Andy Sayler <www.andysayler.com>
# Modified by: Mike Vitousek
# CU CS 5525 - Compilers
# Creation Date: 2012/09/06
# Modififed Date: 2012/09/13
# Description:
#	This is the Makefile for the compiler test files


CC = gcc
PC = ./compile.py
CP = cp
PY = python

CFLAGS = -c -m32 -g
LFLAGS = -m32 -g

SUBMISSIONDIR = ./submission/
HELPERDIR = ./helper/

TESTCASESSOURCE = $(wildcard test/*.py)
TESTCASESASSEMB = $(patsubst test/%.py,test/%.s,$(TESTCASESSOURCE))
TESTCASES = $(patsubst test/%.s,test/%.out,$(TESTCASESASSEMB))
TESTDIFFS = $(patsubst test/%.s,test/%.diff,$(TESTCASESASSEMB))

.PHONY: all test clean submission helper

all: test

helper: runtime.o hashtable.o hashtable_itr.o hashtable_utility.o

test: $(TESTDIFFS)
	cat test/*.diff
	rm *.output *.correct

test/%.diff: test/%.py test/%.out test/%.in
	cat test/$*.in | ./test/$*.out > $*.output
	cat test/$*.in | python test/$*.py > $*.correct
	diff -B -s -q $*.output $*.correct > $@

test/%.out: test/%.s runtime.o hashtable.o hashtable_itr.o hashtable_utility.o
	$(CC) $(LFLAGS) $^ -lm -o $@

test/%.s: test/%.py
	$(PC) $^

runtime.o: helper/runtime.c helper/runtime.h
	$(CC) $(CFLAGS) $< -o $@

hashtable.o: helper/hashtable.c helper/hashtable.h
	$(CC) $(CFLAGS) $< -o $@

hashtable_itr.o: helper/hashtable_itr.c helper/hashtable_itr.h 
	$(CC) $(CFLAGS) $< -o $@

hashtable_utility.o: helper/hashtable_utility.c helper/hashtable_utility.h
	$(CC) $(CFLAGS) $< -o $@

submission:
	$(RM) -r $(SUBMISSIONDIR)
	mkdir $(SUBMISSIONDIR)
	$(CP) *.py $(SUBMISSIONDIR)
	$(CP) -r ply $(SUBMISSIONDIR)
	$(CP) $(HELPERDIR)* $(SUBMISSIONDIR)
	cd $(SUBMISSIONDIR) && zip -r ../submit.zip *
	$(RM) -r $(SUBMISSIONDIR)

clean:
	$(RM) $(TESTCASESASSEMB)
	$(RM) $(TESTCASES)
	$(RM) $(TESTDIFFS)
	$(RM) *.o
	$(RM) *.out
	$(RM) *.s
	$(RM) *~
	$(RM) test/*~
	$(RM) *.pyc
	$(RM) submit.zip
	$(RM) *.output
	$(RM) *.correct
