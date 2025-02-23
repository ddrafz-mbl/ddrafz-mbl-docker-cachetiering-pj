# Base Image
FROM python:3.9-slim

# Set Working Directory
WORKDIR /app

# Copy Requirements and Install Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Application Code
COPY . .

# Expose Port and Run Application
EXPOSE 5000
CMD ["python3", "app.py"]