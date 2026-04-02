# Stage 1 --- Build

FROM python:3.12-slim AS builder

WORKDIR /opt/app-root/src

# copy requirements and install to folder (/install)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=./install -r requirements.txt

# Stage 2 --- runtime 

FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /opt/app-root/src/install /usr/local 

COPY agent/ ./agent/                                              
COPY collector/ ./collector/ 
COPY notifications/ ./notifications/  

# create sangan user and change ownership for sangan
RUN useradd -u 1001 -m sangan && chown -R sangan:sangan /app 

USER sangan 

# run sangan-ai-watcher 
CMD ["python", "-m", "agent.monitor"]

