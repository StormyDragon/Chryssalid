$ErrorActionPreference = "Stop"

docker build -t cloud_build -f .\Dockerfile .
docker create --name cloud_build_instance cloud_build
docker cp cloud_build_instance:/app/package.zip package.zip
docker rm cloud_build_instance
gsutil cp package.zip gs://cloud-stuff/package.zip
gcloud functions deploy hello3 --source gs://cloud-stuff/package.zip --trigger-http
