ARG from=public.ecr.aws/j1r0q0g6/notebooks/notebook-servers/jupyter-scipy:v1.4

FROM ${from}

# see: https://stackoverflow.com/a/69011437
ENV DISPLAY "" 

COPY requirements.txt /tmp
USER root
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg  add - && apt-get update -y && apt-get install google-cloud-cli -y

USER jovyan                  
# see: https://stackoverflow.com/a/69345518
RUN pip install --upgrade pip
RUN pip install -U -r "/tmp/requirements.txt"

RUN mkdir -p "/home/jovyan/.config"
