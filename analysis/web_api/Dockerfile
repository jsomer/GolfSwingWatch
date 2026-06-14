FROM python:3.12-slim

WORKDIR /app

COPY analysis/web_api/requirements.txt /app/analysis/web_api/requirements.txt
RUN pip install --no-cache-dir -r /app/analysis/web_api/requirements.txt

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "analysis.web_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
