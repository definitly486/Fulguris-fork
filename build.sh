#!/bin/sh
./gradlew assembleSlionsFullAgentRelease --offline  -x lint --no-daemon "$@"