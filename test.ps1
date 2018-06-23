$ErrorActionPreference = "Continue"

docker build -t cloud_build -f .\Dockerfile .
docker build -t cloud_test -f examples/Dockerfile.test examples

$run = $(docker run -d -p 82:80 cloud_test)
Start-Sleep -Seconds 1
(Invoke-WebRequest -Uri "http://localhost:82/load")
(Invoke-WebRequest -Uri "http://localhost:82/check")
(Invoke-WebRequest -Uri "http://localhost:82/execute/")
docker logs $run
docker rm -f $run
