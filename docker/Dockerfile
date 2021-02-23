FROM ubuntu:18.04
ARG VERSION=1

LABEL name="Halucinator Testing" \
      version="${VERSION}"

WORKDIR /root/
ENV DEBIAN_FRONTEND="noninteractive"

RUN apt-get update && apt-get install -y sudo automake python3-pip \
	python3-dev build-essential libxml2-dev gdb gdb-multiarch \
	libxslt1-dev git libffi-dev cmake libreadline-dev libtool debootstrap debian-archive-keyring \
	libglib2.0-dev libpixman-1-dev screen binutils-multiarch nasm vim libssl-dev \
	tcpdump g++ 

RUN git clone --recursive https://github.com/embedded-sec/halucinator.git
RUN ["/bin/bash", "-c", "cd /root/halucinator && pip3 install -r src/requirements.txt && pip3 install -e src"] 
RUN ["/bin/bash", "-c", "ln /usr/bin/gdb-multiarch /usr/bin/arm-none-eabi-gdb"]

# Install Avatar2 Qemu
RUN git clone --recursive https://github.com/avatartwo/avatar2.git
RUN ["/bin/bash", "-c", "cd /root/avatar2 && python3 setup.py install && echo yes | /root/avatar2/targets/build_qemu.sh"]

ENV HALUCINATOR_QEMU="/root/avatar2/targets/build/qemu/arm-softmmu/qemu-system-arm"

# To run an example, please refer to https://github.com/embedded-sec/halucinator#running-uart-example
# Open two terminals and type the following commands:
# Terminal 1:
# `hal_dev_uart -i=1073811456`
# Terminal 2:
# `cd /root/halucinator && test/STM32/example/run.sh`
