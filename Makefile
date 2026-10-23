.PHONY: all help install test run docker-build up down logs terraform-init terraform-fmt terraform-validate terraform-plan terraform-apply

VENV ?= .venv
PYTHON ?= $(VENV)/bin/python

all: test

help:
	@printf '%s\n' \
	  'install       Install application and development dependencies' \
	  'test          Run the unit and API tests' \
	  'run           Start the API locally (SQLite by default)' \
	  'docker-build  Build the API image' \
	  'up            Start the API and MariaDB with Docker Compose' \
	  'down          Stop the Compose services' \
	  'logs          Follow Compose service logs' \
	  'terraform-fmt Format Terraform files' \
	  'terraform-plan Plan Azure resources (requires ARM_SUBSCRIPTION_ID)'

install:
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install -r requirements-dev.txt

test: install
	$(PYTHON) -m pytest -q

run: install
	$(PYTHON) -m uvicorn app.main:app --reload

docker-build:
	docker compose build api

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

terraform-init:
	terraform -chdir=infra/terraform init

terraform-fmt:
	terraform fmt -recursive infra/terraform

terraform-validate: terraform-init
	terraform -chdir=infra/terraform validate

terraform-plan: terraform-validate
	terraform -chdir=infra/terraform plan -var="subscription_id=$${ARM_SUBSCRIPTION_ID:?Set ARM_SUBSCRIPTION_ID}"

terraform-apply: terraform-validate
	terraform -chdir=infra/terraform apply -var="subscription_id=$${ARM_SUBSCRIPTION_ID:?Set ARM_SUBSCRIPTION_ID}"