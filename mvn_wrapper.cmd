@echo off
set JAVA_HOME=C:\Users\VWAUCCY\dev\msf\.jdk\jdk-25.0.2+10
set PATH=%JAVA_HOME%\bin;%PATH%
"C:\Users\VWAUCCY\dev\msf\.maven\maven\bin\mvn.CMD" ^
  -Daether.connector.https.securityMode=insecure ^
  -Dmaven.wagon.http.ssl.insecure=true ^
  -Dmaven.wagon.http.ssl.allowall=true ^
  %*
