FROM python:3.10-slim

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt /root/.cache/pip -rf
ADD . /app
WORKDIR /app
CMD ["python", "main.py"]
