FROM debian:buster

MAINTAINER S. Utku DARILMAZ <utkudarilmaz@gmail.com>

LABEL desription="Pronterface, Pronsole, and Printcore Docker image."
LABEL version="1.0"

RUN apt update && \
  apt install -y git python3 python3-venv python3-pip python3-serial \
  python3-numpy cython3 python3-libxml2 python3-gi python3-dbus \
  python3-psutil python3-cairosvg libpython3-dev python3-appdirs \
  python3-wxgtk4.0 && \
  apt clean && \
  rm -rf /var/lib/apt/lists/*

COPY . /root/Printrun

WORKDIR /root/Printrun

ENTRYPOINT ["python3"]
CMD ["pronterface.py"]
