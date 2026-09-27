FROM python:3.12

WORKDIR /app

RUN pip install gunicorn==25.3.0

COPY backend/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

COPY data/ingredients.json /data/ingredients.json

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "foodgram.wsgi:application"]
