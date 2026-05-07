CI_SCAFFOLD_FILES: dict[str, str] = {
    ".github/workflows/validate.yml": """name: validate

on:
  pull_request:
  push:
    branches: [main]

jobs:
  iac-validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: hashicorp/setup-terraform@v3
      - name: Install CLI test dependencies
        run: pip install pytest typer PyYAML
      - name: Run CLI tests
        run: PYTHONPATH=cli/src python -m pytest cli/tests -q
      - name: Terraform fmt
        run: terraform fmt -check -recursive infra/terraform
      - name: Terraform init and validate
        run: |
          cd infra/terraform/environments/homelab
          terraform init -backend=false
          terraform validate
      - name: Ansible syntax check
        run: |
          pipx install ansible
          cd config/ansible
          ansible-playbook -i inventory/static.yml playbooks/post-provision.yml --syntax-check
""",
}

