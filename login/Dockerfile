FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p ./database
COPY models.py ./database/models.py

COPY . .

EXPOSE 8080

CMD ["python", "login.py"]