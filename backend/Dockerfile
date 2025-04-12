FROM python:3.11-slim
WORKDIR /app

# Install nginx
RUN apt-get update && apt-get install -y nginx && apt-get clean

# Copy backend requirements and install dependencies
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# Copy nginx configuration
COPY backend/nginx.conf /etc/nginx/nginx.conf

# Copy backend code to a backend subdirectory
COPY backend/ /app/backend/

# Copy frontend code to a frontend subdirectory
COPY frontend/ /app/frontend/

# Create start script
RUN echo '#!/bin/bash\n\
    service nginx start\n\
    cd /app/backend\n\
    gunicorn --bind 0.0.0.0:5000 main:app &\n\
    wait' > /app/start.sh && chmod +x /app/start.sh

# Expose port 80 for Nginx
EXPOSE 80

# Run the start script
CMD ["/app/start.sh"]