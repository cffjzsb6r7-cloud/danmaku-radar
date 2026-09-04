FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY . .
ENV DANMAKU_CORS="*" DANMAKU_SERVE_WEB="true" DANMAKU_DB="/var/data/danmaku.db"
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
