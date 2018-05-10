$ErrorActionPreference = "Stop"

docker build -t cloud_build -f .\Dockerfile .
docker create --name cloud_build_instance cloud_build
docker cp cloud_build_instance:/app/package.zip package.zip
docker rm cloud_build_instance

python -m deploy --project stormweyr --prefix trigger
