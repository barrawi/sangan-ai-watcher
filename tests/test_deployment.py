"""
test_deployment.py
Post depployment validation, it verifies the running Sangan pod matches
the security spec defined in kubernetes/deployment.yaml
Wilberth Barrantes
"""

import subprocess

import pytest

testinfra = pytest.importorskip(
    "testinfra"
)  # skips entire file if not installed


def get_pod_name():
    result = subprocess.run(
        [
            "kubectl",
            "get",
            "pods",
            "-n",
            "default",
            "-l",
            "app=sangan",
            "-o",
            "jsonpath={.items[0].metadata.name}",
        ],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@pytest.fixture(scope="module")
def host():
    pod_name = get_pod_name()
    assert pod_name, "Could not find sangan pod — is it running?"
    return testinfra.get_host(f"kubectl://{pod_name}?namespace=default")


@pytest.mark.integration
def test_pod_runs_as_non_root(host):
    # check UID is 1001 which should be sangan as set up goes
    user = host.run("id -u")
    assert user.stdout.strip() == "1001"


@pytest.mark.integration
def test_root_filesystem_is_readonly(host):
    # readOnlyRootFilesystem: true in securityContext
    result = host.run("touch /test-write")
    assert result.rc != 0


@pytest.mark.integration
def test_ollama_url_env_var_is_set(host):
    result = host.run("printenv OLLAMA_URL")
    assert result.rc == 0
    assert result.stdout.strip() != ""


@pytest.mark.integration
def test_prometheus_url_env_var_is_set(host):
    result = host.run("printenv PROMETHEUS_URL")
    assert result.rc == 0
    assert result.stdout.strip() != ""


@pytest.mark.integration
def test_no_cap_sys_admin(host):
    # all capabilities dropped in securityContext
    result = host.run("cat /proc/1/status")
    cap_eff = [
        line
        for line in result.stdout.splitlines()
        if line.startswith("CapEff")
    ]
    assert cap_eff, "Could not find CapEff in /proc/1/status"
    cap_value = cap_eff[0].split(":")[1].strip()
    assert cap_value == "0000000000000000"


@pytest.mark.integration
def test_running_process_is_python(host):
    result = host.run("cat /proc/1/cmdline")
    assert "python" in result.stdout
