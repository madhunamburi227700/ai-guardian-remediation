DOCKER_REPOSITORY ?= docker.io/shraddhazpy
IMAGE ?= ai-guardian-remediation
TAG ?= $(shell git rev-parse --short HEAD)
FULL_IMAGE = $(DOCKER_REPOSITORY)/$(IMAGE):$(TAG)
FULL_IMAGE_LATEST = $(DOCKER_REPOSITORY)/$(IMAGE):latest

image-clean:
	-@docker rmi $(FULL_IMAGE) 2>/dev/null || true
	-@docker rmi $(FULL_IMAGE_LATEST) 2>/dev/null || true


## Build the docker image & optionally push it (DOCKER_PUSH=true)
image: image-clean
	docker build \
		-t $(FULL_IMAGE) \
		-t $(FULL_IMAGE_LATEST) \
		.

	@if [ "$(DOCKER_PUSH)" = "true" ]; then \
		echo "Pushing $(FULL_IMAGE) and latest tag..."; \
		docker push $(FULL_IMAGE); \
		docker push $(FULL_IMAGE_LATEST); \
	fi

## Run Uvicorn locally using uv
run:
	uv run uvicorn src.ai_guardian_remediation.main:app --port 8123 --host localhost

## Show config
info:
	@echo "Docker Repository: $(DOCKER_REPOSITORY)"
	@echo "Image:    		  $(IMAGE)"
	@echo "Tag:      		  $(TAG)"
	@echo "Full:     		  $(FULL_IMAGE)"
