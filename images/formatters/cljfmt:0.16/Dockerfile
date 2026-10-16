FROM alpine:3.20
WORKDIR /tmp
RUN apk add --no-cache curl && \
    curl -fsSL https://github.com/weavejester/cljfmt/releases/download/0.16.6/cljfmt-0.16.6-linux-amd64-static.tar.gz \
      | tar -xz -C /usr/local/bin
COPY format.sh .
