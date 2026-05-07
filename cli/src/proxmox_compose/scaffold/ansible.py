ANSIBLE_SCAFFOLD_FILES: dict[str, str] = {
    "config/ansible/ansible.cfg": """[defaults]
inventory = ./inventory/hosts.yml
playbook_dir = .
roles_path = ./roles
host_key_checking = False
stdout_callback = ansible.builtin.default
callback_result_format = yaml
""",
    "config/ansible/inventory/static.yml": """all:
  children:
    debian_vms:
      hosts: {}
    fedora_vms:
      hosts: {}
    debian_lxcs:
      hosts: {}
    existing_hosts:
      hosts: {}
    existing_docker_vms:
      hosts: {}
""",
    "config/ansible/inventory/generated.yml": """all:
  children: {}
""",
    "config/ansible/inventory/group_vars/all/main.yml": """ansible_python_interpreter: /usr/bin/python3

vm_compose_apps: []

lxc_systemd_services: []
""",
    "config/ansible/inventory/group_vars/all/vault.example.yml": """# Encrypt this file as vault.yml using ansible-vault.
#
# example:
# private_repo_deploy_key: |
#   -----BEGIN OPENSSH PRIVATE KEY-----
#   ...
#   -----END OPENSSH PRIVATE KEY-----
#
# frigate_env_content: |
#   MQTT_PASSWORD=...
#   OPENAI_API_KEY=...
#   GEMINI_API_KEY=...
""",
    "config/ansible/inventory/host_vars/example_existing_docker_vm.yml": """# Example host_vars for an existing Docker VM.
# Rename this file to match your inventory host name, for example:
# config/ansible/inventory/host_vars/frigate_vm.yml

vm_compose_apps:
  - dest: "/opt/frigate"
    owner: "root"
    group: "root"
    compose: true
    compose_file_name: "docker-compose.yaml"
    compose_file_content: |
      services:
        frigate:
          image: ghcr.io/blakeblackshear/frigate:0.17.1
          restart: unless-stopped
    env_content: "{{ frigate_env_content }}"
""",
    "config/ansible/playbooks/post-provision.yml": """- name: Configure provisioned VMs and LXCs
  hosts: debian_vms:fedora_vms:debian_lxcs
  become: true
  roles:
    - role: common

- name: Configure Docker workloads on VMs
  hosts: debian_vms:fedora_vms
  become: true
  roles:
    - role: vm_docker

- name: Configure systemd services on Debian LXCs
  hosts: debian_lxcs
  become: true
  roles:
    - role: lxc_systemd_service
""",
    "config/ansible/playbooks/provision-existing.yml": """- name: Converge existing infrastructure
  hosts: existing_hosts
  become: true
  roles:
    - role: common
    - role: existing_maintenance

- name: Converge Docker workloads on existing VMs
  hosts: existing_docker_vms
  become: true
  roles:
    - role: vm_docker
""",
    "config/ansible/roles/common/tasks/main.yml": """- name: Update apt packages
  ansible.builtin.apt:
    update_cache: true
    cache_valid_time: 3600
  when: ansible_facts["os_family"] == "Debian"

- name: Install Debian baseline packages
  ansible.builtin.apt:
    name: "{{ common_packages_debian }}"
    state: present
  when: ansible_facts["os_family"] == "Debian"

- name: Install Fedora baseline packages
  ansible.builtin.dnf:
    name: "{{ common_packages_fedora }}"
    state: present
  when: ansible_facts["distribution"] == "Fedora"
""",
    "config/ansible/roles/common/defaults/main.yml": """common_packages_debian:
  - curl
  - git
  - htop
  - jq
  - python3

common_packages_fedora:
  - curl
  - git
  - htop
  - jq
  - python3
""",
    "config/ansible/roles/vm_docker/tasks/main.yml": """- name: Check whether Docker is already installed
  ansible.builtin.command: docker --version
  register: docker_cli_check
  changed_when: false
  failed_when: false

- name: Install Docker on Debian
  ansible.builtin.apt:
    name:
      - docker.io
      - docker-compose-plugin
    state: present
  when:
    - ansible_facts["os_family"] == "Debian"
    - docker_cli_check.rc != 0

- name: Install Docker on Fedora
  ansible.builtin.dnf:
    name:
      - docker
      - docker-compose
    state: present
  when:
    - ansible_facts["distribution"] == "Fedora"
    - docker_cli_check.rc != 0

- name: Ensure docker service enabled
  ansible.builtin.service:
    name: docker
    enabled: true
    state: started

- name: Deploy compose applications
  ansible.builtin.include_role:
    name: deploy_git_app
  vars:
    deploy_git_apps: "{{ hostvars[inventory_hostname]['vm_compose_apps'] | default([]) }}"
""",
    "config/ansible/roles/vm_docker/defaults/main.yml": """vm_compose_apps: []
""",
    "config/ansible/roles/deploy_git_app/tasks/main.yml": """- name: Ensure app directories exist
  ansible.builtin.file:
    path: "{{ item.dest }}"
    state: directory
    owner: "{{ item.owner | default('root') }}"
    group: "{{ item.group | default('root') }}"
    mode: "0755"
  loop: "{{ deploy_git_apps }}"

- name: Ensure managed file parent directories exist
  ansible.builtin.file:
    path: "{{ item.1.dest | dirname }}"
    state: directory
    owner: "{{ item.1.owner | default(item.0.owner | default('root')) }}"
    group: "{{ item.1.group | default(item.0.group | default('root')) }}"
    mode: "0755"
  loop: "{{ deploy_git_apps | subelements('managed_files', skip_missing=true) }}"

- name: Checkout repositories
  ansible.builtin.git:
    repo: "{{ item.repo }}"
    dest: "{{ item.dest }}"
    version: "{{ item.version | default('main') }}"
    key_file: "{{ item.key_file | default(omit) }}"
    accept_hostkey: true
  loop: "{{ deploy_git_apps }}"
  when: item.repo is defined

- name: Write inline compose files when provided
  ansible.builtin.copy:
    dest: "{{ item.dest }}/{{ item.compose_file_name | default('docker-compose.yaml') }}"
    content: "{{ item.compose_file_content }}"
    owner: "{{ item.owner | default('root') }}"
    group: "{{ item.group | default('root') }}"
    mode: "{{ item.compose_file_mode | default('0644') }}"
  loop: "{{ deploy_git_apps }}"
  when: item.compose_file_content is defined

- name: Write env files when provided
  ansible.builtin.copy:
    dest: "{{ item.dest }}/{{ item.env_file_name | default('.env') }}"
    content: "{{ item.env_content }}"
    owner: "{{ item.owner | default('root') }}"
    group: "{{ item.group | default('root') }}"
    mode: "{{ item.env_file_mode | default('0600') }}"
  no_log: true
  loop: "{{ deploy_git_apps }}"
  when: item.env_content is defined

- name: Write managed files for app stacks
  ansible.builtin.copy:
    dest: "{{ item.1.dest }}"
    content: "{{ item.1.content }}"
    owner: "{{ item.1.owner | default(item.0.owner | default('root')) }}"
    group: "{{ item.1.group | default(item.0.group | default('root')) }}"
    mode: "{{ item.1.mode | default('0644') }}"
  loop: "{{ deploy_git_apps | subelements('managed_files', skip_missing=true) }}"
  no_log: "{{ item.1.secret | default(false) }}"

- name: Deploy compose stacks
  community.docker.docker_compose_v2:
    project_src: "{{ item.dest }}"
    state: present
  when: item.compose | default(true)
  loop: "{{ deploy_git_apps }}"
""",
    "config/ansible/roles/deploy_git_app/defaults/main.yml": """deploy_git_apps: "{{ vm_compose_apps | default([]) }}"
""",
    "config/ansible/roles/lxc_systemd_service/tasks/main.yml": """- name: Install Debian packages for LXC services
  ansible.builtin.apt:
    update_cache: true
    name: "{{ lxc_packages }}"
    state: present

- name: Deploy app repositories for service workloads
  ansible.builtin.include_role:
    name: deploy_git_app
  vars:
    deploy_git_apps: "{{ lxc_git_apps }}"

- name: Ensure go build revision stamp directory exists
  ansible.builtin.file:
    path: /var/lib/ansible-go-revs
    state: directory
    mode: "0755"
  when: lxc_git_apps | selectattr('go_install_path', 'defined') | list | length > 0

- name: Ensure requested Go toolchain version is installed
  ansible.builtin.shell: |
    set -euo pipefail
    version="{{ item.go_version }}"
    case "{{ ansible_architecture }}" in
      x86_64) go_arch="amd64" ;;
      aarch64) go_arch="arm64" ;;
      *)
        echo "Unsupported architecture for Go toolchain bootstrap: {{ ansible_architecture }}" >&2
        exit 1
        ;;
    esac
    current="$(/usr/local/go/bin/go version 2>/dev/null | awk '{print $3}' || true)"
    if [ "$current" = "go${version}" ]; then
      echo "unchanged"
      exit 0
    fi
    url="https://go.dev/dl/go${version}.linux-${go_arch}.tar.gz"
    tarball="/tmp/go${version}.linux-${go_arch}.tar.gz"
    export GO_URL="$url"
    export GO_TARBALL="$tarball"
    python3 - <<'PY'
    import os
    import urllib.request
    urllib.request.urlretrieve(os.environ["GO_URL"], os.environ["GO_TARBALL"])
    PY
    rm -rf /usr/local/go
    tar -C /usr/local -xzf "$tarball"
    ln -sf /usr/local/go/bin/go /usr/local/bin/go
    ln -sf /usr/local/go/bin/gofmt /usr/local/bin/gofmt
    rm -f "$tarball"
    echo "installed"
  args:
    executable: /bin/bash
  loop: "{{ lxc_git_apps }}"
  when:
    - item.go_version is defined
    - item.go_version | length > 0
  register: lxc_go_toolchain_results
  changed_when: >
    not (lxc_go_toolchain_results.skipped | default(false))
    and (
      'installed' in (lxc_go_toolchain_results.results | default([])
        | selectattr('stdout', 'defined')
        | map(attribute='stdout')
        | join(''))
      or 'installed' in (lxc_go_toolchain_results.stdout | default(''))
    )

- name: Go build install for LXC git apps
  ansible.builtin.shell: |
    set -e
    cd "{{ item.dest }}"
    head=$(git rev-parse HEAD)
    stamp="/var/lib/ansible-go-revs/{{ item.go_install_path | regex_replace('^/', '') | replace('/', '_') }}.rev"
    if [ -f "$stamp" ] && [ "$(cat "$stamp")" = "$head" ] && [ -f "{{ item.go_install_path }}" ]; then
      echo "unchanged"
      exit 0
    fi
    GO_BIN="$(command -v go || true)"
    if [ -x /usr/local/go/bin/go ]; then
      GO_BIN="/usr/local/go/bin/go"
    fi
    if [ -z "$GO_BIN" ]; then
      echo "go binary not found in PATH and /usr/local/go/bin/go is missing" >&2
      exit 1
    fi
    "$GO_BIN" build {{ (item.go_build_args | default([])) | map('quote') | join(' ') }} -o "{{ item.go_install_path }}" .
    printf '%s' "$head" > "$stamp"
    echo "rebuilt"
  args:
    executable: /bin/bash
  loop: "{{ lxc_git_apps }}"
  environment: "{{ item.go_build_environment | default({}) }}"
  when:
    - item.repo is defined
    - item.go_install_path is defined
  register: lxc_go_build_results
  changed_when: >
    not (lxc_go_build_results.skipped | default(false))
    and (
      'rebuilt' in (lxc_go_build_results.results | default([])
        | selectattr('stdout', 'defined')
        | map(attribute='stdout')
        | join(''))
      or 'rebuilt' in (lxc_go_build_results.stdout | default(''))
    )
  notify: Restart LXC services

- name: Install systemd unit files
  ansible.builtin.template:
    src: service.j2
    dest: "/etc/systemd/system/{{ item.name }}.service"
    mode: "0644"
  loop: "{{ lxc_systemd_services }}"
  notify: Restart LXC services

- name: Enable and start services
  ansible.builtin.service:
    name: "{{ item.name }}"
    enabled: true
    state: started
  loop: "{{ lxc_systemd_services }}"
""",
    "config/ansible/roles/lxc_systemd_service/defaults/main.yml": """lxc_packages:
  - postgresql
  - redis-server

lxc_git_apps: []

lxc_systemd_services: []
""",
    "config/ansible/roles/lxc_systemd_service/handlers/main.yml": """- name: Restart LXC services
  ansible.builtin.systemd:
    daemon_reload: true
    name: "{{ item.name }}"
    state: restarted
  loop: "{{ lxc_systemd_services }}"
""",
    "config/ansible/roles/lxc_systemd_service/templates/service.j2": """[Unit]
Description={{ item.description | default(item.name) }}
After=network-online.target

[Service]
Type=simple
User={{ item.user | default('root') }}
WorkingDirectory={{ item.working_dir | default('/') }}
{% if item.environment_file is defined and item.environment_file | length > 0 %}
EnvironmentFile={{ item.environment_file }}
{% endif %}
{% if item.environment_files is defined %}
{% for ef in item.environment_files %}
EnvironmentFile={{ ef }}
{% endfor %}
{% endif %}
ExecStart={{ item.exec_start }}
Restart=always
RestartSec=5
{% if item.environment is defined and item.environment | length > 0 %}
Environment={{ item.environment }}
{% endif %}

[Install]
WantedBy=multi-user.target
""",
    "config/ansible/roles/existing_maintenance/tasks/main.yml": """- name: Run host update script if configured
  ansible.builtin.shell: "{{ existing_update_script }}"
  args:
    executable: /bin/bash
  when: existing_update_script | length > 0

- name: Install lm-sensors on Debian/Fedora
  ansible.builtin.package:
    name: lm-sensors
    state: present
""",
    "config/ansible/roles/existing_maintenance/defaults/main.yml": """existing_update_script: ""
""",
}

