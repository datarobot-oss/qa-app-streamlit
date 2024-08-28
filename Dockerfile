FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY ./packages/dr_components-0.1.4-py3-none-any.whl /app/

RUN pip3 install --no-cache-dir 'streamlit==1.31.0' 'streamlit_extras==0.3.6' 'datarobot==3.3.1' 'responses==0.22.0'
RUN pip3 install --no-cache-dir ./dr_components-0.1.4-py3-none-any.whl

WORKDIR /opt/code

EXPOSE 8080

ENTRYPOINT ./start-app.sh