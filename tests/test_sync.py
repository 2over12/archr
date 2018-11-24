import pygdbmi.gdbcontroller
import archr
import angr
import os

def setup_module():
    os.system("cd %s/dockers; ./build_all.sh" % os.path.dirname(__file__))

def parse_output(s):
    return { w.split(b":")[0]: int(w.split(b":")[1], 16) for w in s.splitlines() }

def do_gdb(t):
    with archr.arsenal.GDBServerBow(t).fire_context(port=31337) as gbf:
        gc = pygdbmi.gdbcontroller.GdbController()
        gc.write("target remote %s:%d" % (t.ipv4_address, 31337))
        gc.write("continue")
        gc.exit()
        return gbf

def do_qemu(t):
    with archr.arsenal.QEMUTracerBow(t).fire_context() as qbf:
        return qbf.process

def test_env():
    with archr.targets.DockerImageTarget('archr-test:entrypoint-env').build() as t:
        reference_env = t.run_command(aslr=False).stdout.read()
        gdb_env = do_gdb(t).stdout.read()
        assert set(reference_env.splitlines()) == set(gdb_env.splitlines())
        qemu_env = do_qemu(t).stdout.read()
        assert set(reference_env.splitlines()) == set(qemu_env.splitlines())

def check_offsetprinter(t):
    reference_str = t.run_command(aslr=False).stdout.read()
    reference_dct = parse_output(reference_str)
    assert parse_output(t.run_command(aslr=False).stdout.read()) == reference_dct

    gdb_str = do_gdb(t).stdout.read()
    assert parse_output(gdb_str) == reference_dct

    qemu_str = do_qemu(t).stdout.read()
    qemu_dct = parse_output(qemu_str)
    for s in [ b'MAIN',  b'STDOUT', b'SMALL_MALLOC', b'BIG_MALLOC', b'MMAP' ]:
        assert hex(qemu_dct[s])[-3:] == hex(reference_dct[s])[-3:]
    assert qemu_dct[b'STACK'] - qemu_dct[b'ARGV'] == reference_dct[b'STACK'] - reference_dct[b'ARGV']
    assert qemu_dct[b'STACK'] - qemu_dct[b'ENVP'] == reference_dct[b'STACK'] - reference_dct[b'ENVP']

    dsb = archr.arsenal.DataScoutBow(t)
    apb = archr.arsenal.angrProjectBow(t, dsb)
    asb = archr.arsenal.angrStateBow(t, apb)
    project = apb.fire(use_sim_procedures=False)
    state = asb.fire(add_options={angr.sim_options.STRICT_PAGE_ACCESS}) # for now
    simgr = project.factory.simulation_manager(state)
    #assert not simgr.active[0].memory.load(0x7ffff7dd48f8, project.arch.bytes).symbolic # __libc_multiple_threads sanity check
    simgr.run()
    assert len(simgr.errored) == 0
    assert len(simgr.deadended) == 1
    assert len(sum(simgr.stashes.values(), [])) == 1
    assert simgr.deadended[0].posix.dumps(1) == reference_str

def test_offsetprinter64():
    #with archr.targets.DockerImageTarget('archr-test:offsetprinter').build() as t:
    t = archr.targets.DockerImageTarget('archr-test:offsetprinter64').build().start()
    check_offsetprinter(t)
    t.stop()

def test_offsetprinter32():
    #with archr.targets.DockerImageTarget('archr-test:offsetprinter').build() as t:
    t = archr.targets.DockerImageTarget('archr-test:offsetprinter32', target_arch='i386').build().start()
    check_offsetprinter(t)
    t.stop()

def test_stack():
    t = archr.targets.DockerImageTarget('archr-test:stackprinter64').build().start()
    reference_str = t.run_command(aslr=False).stdout.read()

    dsb = archr.arsenal.DataScoutBow(t)
    apb = archr.arsenal.angrProjectBow(t, dsb)
    asb = archr.arsenal.angrStateBow(t, apb)
    project = apb.fire(use_sim_procedures=False)
    state = asb.fire(add_options={angr.sim_options.STRICT_PAGE_ACCESS}) # for now
    simgr = project.factory.simulation_manager(state)
    simgr.run()
    assert len(simgr.errored) == 0
    assert len(simgr.deadended) == 1
    assert len(sum(simgr.stashes.values(), [])) == 1
    assert simgr.deadended[0].posix.dumps(1) == reference_str

if __name__ == '__main__':
    test_offsetprinter32()
    test_offsetprinter64()
    test_stack()
    test_env()