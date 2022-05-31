ARG from=python:slim
FROM ${from}

WORKDIR /app

COPY requirements.txt /app
RUN \
  pip3 install --upgrade pip && \
  pip3 install --no-cache-dir -r requirements.txt && \
  rm -rf /app/requirements.txt

COPY src/main.py /app
ENTRYPOINT [ "kopf", "run", "main.py", "--log-format=plain", "--standalone", "--all-namespaces"]
EXPOSE 9229
