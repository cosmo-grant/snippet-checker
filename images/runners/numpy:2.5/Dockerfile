FROM python:3.13
WORKDIR /tmp
ENV NO_COLOR=true PYTHONWARNINGS=ignore
COPY prepare.sh run.sh ./
RUN <<EOF
python -m venv numpy_env
. numpy_env/bin/activate
python -m pip install --no-cache-dir numpy==2.5
EOF
