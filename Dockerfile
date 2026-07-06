FROM ubuntu:latest
LABEL authors="artemdordyuk"

ENTRYPOINT ["top", "-b"]