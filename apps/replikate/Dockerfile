ARG from=python:slim
FROM ${from}

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
