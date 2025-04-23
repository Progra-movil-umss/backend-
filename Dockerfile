FROM python:3.11-slim

WORKDIR /app

COPY requirements/prod.txt requirements/prod.txt
COPY requirements/base.txt requirements/base.txt

RUN pip install --no-cache-dir -r requirements/prod.txt

COPY . /app/

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"] 