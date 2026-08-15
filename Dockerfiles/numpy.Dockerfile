# the notes should not be sensitive to the python3 version, so use "latest" tag
FROM python:latest
ARG numpy_version
RUN <<EOF
python -m venv numpy_env
. numpy_env/bin/activate
python -m pip install --no-cache-dir numpy==${numpy_version}
EOF
