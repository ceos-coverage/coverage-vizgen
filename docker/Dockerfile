FROM centos:7

COPY ./docker/run-onearth.sh /usr/local/bin/run-vizgen.sh
COPY ./src/vizgen/* /usr/local/bin/
COPY ./vizgen/bin/* /usr/local/bin/

RUN yum -y install epel-release wget python3 python3-devel git gcc
RUN wget https://github.com/nasa-gibs/onearth/releases/download/v1.4.0/onearth-1.4.0-8.el7.tar.gz
RUN tar -zxvf onearth-*.tar.gz && yum -y install gibs-gdal-* && yum -y install onearth-* && yum clean all && rm -f *.rpm *tar.gz
RUN yum -y install numpy proj-devel nco && yum clean all

# Install conda
RUN curl -sSL https://repo.anaconda.com/miniconda/Miniconda3-4.7.12.1-Linux-x86_64.sh -o /tmp/miniconda.sh \
    && bash /tmp/miniconda.sh -bfp /usr/local/ \
    && conda install -y python=3 \
    && conda update conda \
    && conda clean --all --yes

# Upgrade GDAL
RUN conda install -c conda-forge -y gdal==3.4.0 \
    && conda clean --all --yes

# Get newer version of mrfgen
RUN git clone https://github.com/nasa-gibs/onearth.git -b 2.6.2 --single-branch
ENV ONEARTH_VERSION 2.6.2
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

RUN pip3 install pathlib pyaml Pillow==8.1.0
ENV LCDIR=/etc/onearth/config
RUN sed -i 's/Order allow,deny/Require all granted/g' /etc/httpd/conf.d/onearth-demo.conf

COPY ./colormaps/ /etc/onearth/colormaps
RUN mkdir -p /usr/share/onearth/mrfgen/configs /usr/share/onearth/mrfgen/working_dir && \
    cp /usr/share/onearth/mrfgen/Blank_RGBA_512.png /usr/share/onearth/mrfgen/transparent.png

RUN chmod -R 755 /usr/share/onearth/mrfgen/
WORKDIR /vizgen/
RUN rm -rf /onearth/

# Start HTTPD server
CMD sh /usr/local/bin/run-vizgen.sh
