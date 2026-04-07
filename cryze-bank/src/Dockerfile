FROM docker.io/sagemath/sagemath@sha256:19995db6194f4a4bab18ce9a88556fd15b9ed5e916b4504fefe618a7796ddbdb

#ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

USER 0
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        fontconfig \
        libfreetype6 \
        libjpeg-turbo8 \
        libpng16-16 \
        libx11-6 \
        libxext6 \
        libxrender1 \
        python3 \
        python3-pip \
        xfonts-75dpi \
        xfonts-base \
    && curl -fsSL -o /tmp/libssl1.1.deb \
        http://archive.ubuntu.com/ubuntu/pool/main/o/openssl/libssl1.1_1.1.1f-1ubuntu2.24_amd64.deb \
    && curl -fsSL -o /tmp/wkhtmltox.deb \
        https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.5/wkhtmltox_0.12.5-1.focal_amd64.deb \
    && apt-get install -y --no-install-recommends /tmp/libssl1.1.deb /tmp/wkhtmltox.deb \
    && rm -f /tmp/libssl1.1.deb /tmp/wkhtmltox.deb \
    && wkhtmltopdf --version | grep -F "0.12.5" \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app/cryze-bank/
COPY requirements.txt /app/requirements.txt

RUN mkdir -p /app/data
RUN chown -R 1000:1000 /app

USER 1000
RUN sage -pip install --no-cache-dir --upgrade -r /app/requirements.txt 

WORKDIR /app/cryze-bank

RUN sage -preparse curve_gen.sage
RUN sage curve_gen.sage.py >/dev/null

EXPOSE 5000

CMD ["python3", "server.py"]
