FROM python:3.6.8-slim-stretch

LABEL maintainer="folusomaine"

COPY . /app

COPY requirements.txt /app/requirements.txt

WORKDIR /app

# RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ENV FLASK_APP=access_auth.py

EXPOSE 5000

# ENTRYPOINT ["python"]

CMD ["flask", "run", "--host", "0.0.0.0"]