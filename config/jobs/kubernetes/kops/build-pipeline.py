# Copyright 2020 The Kubernetes Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json

branches = [
    "master",
    "1.19",
    "1.18",
]
master_k8s_version = "1.20"

template = """
# Verify the latest-ci version from the {{branch}} branch of kops
# Runs a small subset of the e2e tests.
# Publishes the version to latest-ci-updown-green on success.
- interval: 60m
  name: {{name}}
  decorate: true
  decoration_config:
    timeout: 45m
  labels:
    preset-service-account: "true"
    preset-aws-ssh: "true"
    preset-aws-credential: "true"
  spec:
    containers:
    - image: {{e2e_image}}
      env:
      - name: KOPS_RUN_TOO_NEW_VERSION
        value: "1"
      command:
      - runner.sh
      - kubetest
      args:
      # Generic e2e test args
      - --up
      - --test
      - --down
      - --dump=$(ARTIFACTS)
      - --timeout=45m
      - --gcp-service-account=$(E2E_GOOGLE_APPLICATION_CREDENTIALS)
      # kops-specific test args
      - --deployment=kops
      - --provider=aws
      - --cluster={{name}}.test-cncf-aws.k8s.io
      - --kops-ssh-user=ubuntu
      - --kops-nodes=4
      - --extract={{extract}}
      - --kops-state=s3://k8s-kops-prow/
      - --kops-ssh-key=$(AWS_SSH_PRIVATE_KEY_FILE)
      - --kops-ssh-public-key=$(AWS_SSH_PUBLIC_KEY_FILE)
      # We don't have permission to write to gs://k8s-staging-kops
      - --kops-publish=gs://kops-ci/markers/{{branch}}/latest-ci-updown-green.txt
      # Published by the kops staging build jobs
      - --kops-version=https://storage.googleapis.com/k8s-staging-kops/kops/releases/markers/{{branch}}/latest-ci.txt
      #- --kops-kubernetes-version should be inferred by kubetest from --extract
      #- --kops-zone should be randomized by kubetest
      # Specific test args
      - --test_args=--ginkgo.focus=\\[k8s.io\\]\\sNetworking.*\\[Conformance\\] --ginkgo.skip=\\[Slow\\]|\\[Serial\\]
      - --ginkgo-parallel
  annotations:
    testgrid-dashboards: sig-cluster-lifecycle-kops, google-aws, kops-misc, kops-k8s-{{k8s_version}}
    testgrid-tab-name: {{tab}}
"""

def build_tests(branch, k8s_version):
    def expand(s):
        subs = {}
        if k8s_version:
            subs['k8s_version'] = k8s_version
        if branch:
            subs['branch'] = branch
        return s.format(**subs)

    if branch == 'master':
        extract = "release/latest-" + master_k8s_version
        e2e_image = "gcr.io/k8s-testimages/kubekins-e2e:v20201215-73fe430-master"
    else:
        extract = expand("release/stable-{k8s_version}")
        # Hack to stop the autobumper getting confused
        e2e_image = "gcr.io/k8s-testimages/kubekins-e2e:v20201215-73fe430-1.19"
        e2e_image = e2e_image[:-4] + k8s_version

    tab = expand('kops-pipeline-updown-{branch}')

    # Names must be valid pod and DNS names
    name = expand('e2e-kops-pipeline-updown-kops{branch}')
    name = name.replace('.', '')

    y = template
    y = y.replace('{{extract}}', extract)
    y = y.replace('{{e2e_image}}', e2e_image)
    y = y.replace('{{k8s_version}}', k8s_version)
    y = y.replace('{{name}}', name)
    y = y.replace('{{tab}}', tab)

    if branch == 'master':
        y = y.replace('{{branch}}', "master")
    else:
        y = y.replace('{{branch}}', "release-" + branch)

    spec = {
        'branch': branch,
        'k8s_version': k8s_version,
    }
    jsonspec = json.dumps(spec, sort_keys=True)

    print("")
    print("# " + jsonspec)
    print(y.strip())

def generate():
    print("# Test scenarios generated by build-pipeline.py (do not manually edit)")
    print("periodics:")
    for branch in branches:
        k8s_version = master_k8s_version if branch == "master" else branch
        build_tests(branch=branch, k8s_version=k8s_version)

generate()
