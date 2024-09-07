# Use an official Python runtime as a base image
FROM python:3.8-slim

# Install system dependencies required for psycopg2
RUN apt-get update && apt-get install -y libpq-dev gcc locales

# Generate en_US.UTF-8 and en_AU.UTF-8 locales
RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    echo "en_AU.UTF-8 UTF-8" >> /etc/locale.gen && \
    locale-gen

# Set the default locale for the environment
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install development requirements
RUN pip install --no-cache-dir -r requirements-dev.txt

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run app.py when the container launches using uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
