ARG from=python:3.10-slim
FROM ${from}

LABEL org.opencontainers.image.source="https://github.com/epam/hub-kubeflow-stacks"
LABEL org.opencontainers.image.authors="Antons Kranga <antons_kranga@epam.com>"
LABEL org.opencontainers.image.description="Replicates configuration across multiple namespaces"
LABEL org.opencontainers.image.licenses=MPL-2.0

WORKDIR /app

RUN apt-get update && apt-get install -y \
  tk \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app
RUN \
  pip3 install --upgrade pip && \
  pip3 install --no-cache-dir -r requirements.txt && \
  rm -rf /app/requirements.txt

COPY src/main.py /app
ENTRYPOINT [ "kopf", "run", "main.py", "--log-format=plain", "--standalone", "--all-namespaces"]
EXPOSE 9229
