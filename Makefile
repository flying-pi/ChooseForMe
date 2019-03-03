WORKDIR := $(shell pwd)

help: ## Display help message
	@echo "Please use \`make <target>' where <target> is one of"
	@perl -nle'print $& if m{^[\.a-zA-Z_-]+:.*?## .*$$}' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}'

run_app_with_console: .build/app_image ## Run with  input ssuport
	export WORKDIR=$(WORKDIR); docker-compose up -d && docker attach choose_for_me

run_app: .build/app_image ## Run application
	export WORKDIR=$(WORKDIR); docker-compose up

.build/app_image: .build requirements.txt  Dockerfile
	docker build -t choose_for_me:latest -f Dockerfile .
	touch .build/app_image

.build:
	mkdir .build
