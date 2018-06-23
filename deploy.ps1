$ErrorActionPreference = "Stop"
$ProjectName = "stormweyr"
$TriggerName = "hello-trigger"

docker build -t cloud_build -f .\Dockerfile .
docker build -t cloud_example -f examples\Dockerfile examples

docker run --rm -it -v ${ServiceAccount}:/service-account.json:ro cloud_example --http --project=${ProjectName} --name=${TriggerName}
