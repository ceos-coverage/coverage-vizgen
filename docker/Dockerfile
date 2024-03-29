FROM centos:7

COPY ./docker/run-vizgen.sh /usr/local/bin/run-vizgen.sh
COPY ./bin/* /usr/local/bin/

RUN yum -y install epel-release wget python3 python3-devel git gcc
RUN wget https://github.com/nasa-gibs/onearth/releases/download/v1.4.0/onearth-1.4.0-8.el7.tar.gz
RUN tar -zxvf onearth-*.tar.gz && yum -y install gibs-gdal-* && yum -y install onearth-* && yum clean all && rm -f *.rpm *tar.gz
RUN yum -y install numpy proj-devel nco && yum clean all

# Install conda
RUN curl -sSL https://repo.anaconda.com/miniconda/Miniconda3-4.7.12.1-Linux-x86_64.sh -o /tmp/miniconda.sh \
    && bash /tmp/miniconda.sh -bfp /usr/local/ \
    && conda install -y python=3.9 \
    && conda update conda \
    && conda clean --all --yes

# Upgrade GDAL
RUN conda install -c conda-forge -y gdal==3.7.1 \
    && conda clean --all --yes

# Get newer version of mrfgen
RUN git clone https://github.com/nasa-gibs/onearth.git -b 2.6.3 --single-branch
ENV ONEARTH_VERSION 2.6.3
ENV PROJ_LIB=/usr/local/share/proj/
WORKDIR /onearth/src/mrfgen

RUN python3 -m pip install --user --upgrade cython
RUN python3 setup.py build_ext --inplace

RUN mv RgbToPalLib* /usr/bin/
RUN chmod 777 /usr/bin/RgbToPalLib*
RUN install -m 755 mrfgen.py -D /usr/bin/mrfgen
RUN install -m 755 RgbPngToPalPng.py -D /usr/bin/RgbPngToPalPng.py
RUN install -m 755 colormap2vrt.py -D /usr/bin/colormap2vrt.py
RUN install -m 755 overtiffpacker.py -D /usr/bin/overtiffpacker.py
RUN install -m 755 oe_validate_palette.py -D /usr/bin/oe_validate_palette.py
RUN install -m 755 ../scripts/oe_utils.py -D /usr/bin/oe_utils.py

COPY ./requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt
RUN pip3 install fsspec
RUN pip3 install s3fs
ENV LCDIR=/etc/onearth/config
RUN sed -i 's/Order allow,deny/Require all granted/g' /etc/httpd/conf.d/onearth-demo.conf

RUN mkdir /etc/onearth/colormaps
RUN mkdir -p /usr/share/onearth/mrfgen/configs /usr/share/onearth/mrfgen/working_dir && \
    cp /usr/share/onearth/mrfgen/Blank_RGBA_512.png /usr/share/onearth/mrfgen/transparent.png

RUN chmod -R 755 /usr/share/onearth/mrfgen/
WORKDIR /vizgen/
RUN rm -rf /onearth/
RUN mkdir /vizgen/logs/
COPY ./docker/crontab /vizgen/crontab
COPY ./docker/cron.sh /vizgen/cron.sh

# Install supercronic
ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.1.12/supercronic-linux-amd64 \
    SUPERCRONIC=supercronic-linux-amd64 \
    SUPERCRONIC_SHA1SUM=048b95b48b708983effb2e5c935a1ef8483d9e3e

RUN curl -fsSLO "$SUPERCRONIC_URL" \
 && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
 && chmod +x "$SUPERCRONIC" \
 && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
 && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic

# Start HTTPD server
CMD sh /usr/local/bin/run-vizgen.sh
