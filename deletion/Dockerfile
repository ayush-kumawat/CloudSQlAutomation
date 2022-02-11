FROM ubuntu:18.04
RUN apt update
RUN apt -y install software-properties-common
RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt update
RUN apt -y install python3
RUN apt -y install python3-pip
COPY ./requirements.txt /
RUN pip3 install -r /requirements.txt
RUN mkdir -p /app
ADD . /app
WORKDIR /app
CMD ["python3", "-u", "server.py"]