FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .
# Copy all the files from the current directory to the container

CMD ["python", "app.py"]
