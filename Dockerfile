# Optional containerized deployment. The primary deployment path stays
# `py -3 app.py` via Windows Task Scheduler (see README.txt) -- this is
# an alternative for running the same app under Docker.
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
