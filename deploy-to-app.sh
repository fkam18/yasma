#!/bin/bash
set -e

./build.sh
#ssh-keygen -R app2.alt                # remove stale host key
#ssh-keygen -R $(dig +short app2.alt)  # also by IP, if needed
#rm -rf ~/.ansible/cp/*                # remove Ansible’s connection cache
ansible-playbook -i ansible/inventory.ini ansible/deploy.yml
