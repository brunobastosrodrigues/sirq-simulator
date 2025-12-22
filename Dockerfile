FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project folder
COPY . .

# Add /app to PYTHONPATH so src.module works
ENV PYTHONPATH="${PYTHONPATH}:/app"

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
