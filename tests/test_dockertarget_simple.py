import socket
import archr
import time
import os

def setup_module():
    os.system("cd %s/dockers; ./build_all.sh" % os.path.dirname(__file__))

def test_cat():
    with archr.targets.DockerImageTarget('archr-test:cat').build() as t:
        p = t.run_command()
        p.stdin.write(b"Hello!\n")
        assert p.stdout.read(7) == b"Hello!\n"

def test_cat_stderr():
    with archr.targets.DockerImageTarget('archr-test:cat-stderr').build() as t:
        p = t.run_command()
        p.stdin.write(b"Hello!\n")
        assert p.stderr.read(7) == b"Hello!\n"

def test_entrypoint_true():
    with archr.targets.DockerImageTarget('archr-test:entrypoint-true').build() as t:
        p = t.run_command()
        p.wait()
        assert p.returncode == 0

def test_entrypoint_false():
    with archr.targets.DockerImageTarget('archr-test:entrypoint-false').build() as t:
        p = t.run_command()
        p.wait()
        assert p.returncode == 1

def test_entrypoint_crasher():
    with archr.targets.DockerImageTarget('archr-test:crasher').build() as t:
        p = t.run_command()
        p.wait()
        assert p.returncode == 139

def test_entrypoint_env():
    with archr.targets.DockerImageTarget('archr-test:entrypoint-env').build() as t:
        p = t.run_command()
        stdout,_ = p.communicate()
        assert b"ARCHR=YES" in stdout.split(b'\n')

def test_nccat_simple():
    with archr.targets.DockerImageTarget('archr-test:nccat').build() as t:
        t.run_command()
        assert t.tcp_ports == [ 1337 ]
        try:
            s = socket.create_connection((t.ipv4_address, 1337))
        except ConnectionRefusedError:
            time.sleep(5)
            s = socket.create_connection((t.ipv4_address, 1337))
        s.send(b"Hello\n")
        assert s.recv(6) == b"Hello\n"

def test_context_env():
    with archr.targets.DockerImageTarget('archr-test:entrypoint-env').build() as t:
        with t.run_command() as p:
            stdout,_ = p.communicate()
        assert b"ARCHR=YES" in stdout.split(b'\n')

if __name__ == '__main__':
    test_entrypoint_crasher()
    test_context_env()
    test_cat()
    test_cat_stderr()
    test_entrypoint_true()
    test_entrypoint_false()
    test_entrypoint_env()
    test_nccat_simple()
