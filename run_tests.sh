#! /bin/bash
if [ -e coverage.xml ]; then
	rm coverage.xml
fi

py.test --junitxml=testreport.xml --cov-config .coveragerc --cov OPSI --cov-report xml --quiet tests/
