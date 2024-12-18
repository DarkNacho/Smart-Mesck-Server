FROM python:3.12-alpine

# Install wkhtmltopdf dependencies
RUN apk add --no-cache \
    build-base \
    libffi-dev \
    openssl-dev \
    poppler-utils \
    ttf-freefont \
    wkhtmltopdf

# Set the working directory
WORKDIR /app

# Copy only the necessary files
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Expose the port that FastAPI will run on
EXPOSE 8088

# Command to run your FastAPI application with uvicorn
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8088", "--reload"]
