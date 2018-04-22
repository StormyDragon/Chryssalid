FROM python AS py_build

WORKDIR /app
ENV PYENV_ROOT="/app/pyenv" \
    PATH="$PYENV_ROOT/bin:$PATH"
RUN git clone https://github.com/pyenv/pyenv.git pyenv \
 && ./pyenv/bin/pyenv install 3.6.5 \
 && ./pyenv/versions/3.6.5/bin/python -m pip install pipenv
COPY cloud_func/Pipfile cloud_func/Pipfile.lock ./
RUN ./pyenv/versions/3.6.5/bin/python -m pipenv lock --requirements > requirements.txt \
 && ./pyenv/versions/3.6.5/bin/python -m pip install -r requirements.txt

FROM gcr.io/google-appengine/nodejs as final
RUN install_node v6.11.5
RUN apt-get update \
 && apt-get install -y zip
COPY --from=py_build /app/pyenv/versions/3.6.5 /app/python
WORKDIR /tmp/cloud_worker
COPY google_cloud_worker/yarn.lock google_cloud_worker/package.json ./
RUN yarn install
COPY google_cloud_worker/worker.js ./
WORKDIR /app
COPY cloud_func/package.json cloud_func/yarn.lock ./
RUN yarn install
COPY cloud_func ./
RUN zip -9 -r package.zip .

ENV \
    X_GOOGLE_CODE_LOCATION=/app \
    X_GOOGLE_ENTRY_POINT=hello \
    X_GOOGLE_SUPERVISOR_HOSTNAME=192.168.86.101 \
    X_GOOGLE_SUPERVISOR_INTERNAL_PORT=8080 \
    X_GOOGLE_FUNCTION_TRIGGER_TYPE=HTTP_TRIGGER \
    X_GOOGLE_FUNCTION_TIMEOUT_SEC=60 \
    X_GOOGLE_WORKER_PORT=80

CMD ["node", "/tmp/cloud_worker/worker.js"]
