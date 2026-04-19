#!/bin/bash
# Wrapper: overrides Java compiler target to 21 so eqasim-java builds on JDK 22
exec "C:/Users/VWAUCCY/dev/msf/.maven/maven/bin/mvn.CMD" \
  -Dmaven.compiler.source=21 \
  -Dmaven.compiler.target=21 \
  -Daether.connector.https.securityMode=insecure \
  -Dmaven.wagon.http.ssl.insecure=true \
  -Dmaven.wagon.http.ssl.allowall=true \
  "$@"
