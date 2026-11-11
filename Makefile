.PHONY: install test build run down logs azure-login terraform-init terraform-fmt terraform-validate terraform-plan terraform-apply terraform-destroy terraform-destroy-paid

TF_SUB = $${ARM_SUBSCRIPTION_ID:-$$(az account show --query id -o tsv)}
TF_VARS = -var="subscription_id=$(TF_SUB)"
VENV ?= .venv
PYTHON ?= $(VENV)/bin/python
TF_DIR := infra/terraform

#
## Python targets
#

install:
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install -r requirements-dev.txt

test: install
	$(PYTHON) -m pytest -q

#
## Docker targets
#

build:
	docker compose build api

run: build
	docker compose up

down:
	docker compose down

logs:
	docker compose logs -f

#
## Terraform targets
#

azure-login:
	@az account show >/dev/null 2>&1 || az login

terraform-init:
	terraform -chdir=$(TF_DIR) init

terraform-fmt:
	terraform -chdir=$(TF_DIR) fmt -recursive

terraform-validate: terraform-init
	terraform -chdir=$(TF_DIR) validate

terraform-plan: azure-login terraform-validate
	terraform -chdir=$(TF_DIR) plan $(TF_VARS)

terraform-apply: azure-login terraform-validate
	terraform -chdir=$(TF_DIR) apply $(TF_VARS)

terraform-destroy: azure-login terraform-validate
	terraform -chdir=$(TF_DIR) destroy $(TF_VARS)

terraform-destroy-paid: azure-login terraform-validate
	terraform -chdir=$(TF_DIR) destroy \
	  -target=azurerm_linux_web_app.api \
	  -target=azurerm_service_plan.comments \
	  -target=azurerm_cognitive_account.language \
	  -target=azurerm_mysql_flexible_server.comments \
	  $(TF_VARS)