"""SEC-01 : le pod partage-t-il le noyau du nœud ?

runc : attendu = même noyau que le nœud. kata : attendu = noyau invité distinct.
"""

META = {
    "id": "SEC-01",
    "category": "SEC",
    "aspect": "SEC",
    "priority": "P1",
    "title": "Identification du noyau vu par le pod",
}


def run(ctx):
    ctx.apply_template("probe-pod.yaml.j2")
    ctx.wait("pod/probe")

    rc, uname, err = ctx.exec("probe", ["uname", "-r"])
    assert rc == 0, f"uname a échoué : {err}"
    pod_kernel = uname.strip()
    node_kernel = ctx.pod_node("probe")["status"]["nodeInfo"]["kernelVersion"]
    ctx.evidence("proc_version.txt", ctx.exec("probe", ["cat", "/proc/version"])[1])

    shared = pod_kernel == node_kernel
    ctx.metric("kernel_shared_with_node", int(shared), "bool", "lower")
    ctx.observe(f"noyau pod={pod_kernel} ; noyau nœud={node_kernel}")

    expected_shared = ctx.runtime == "runc"
    return "PASS" if shared == expected_shared else "FAIL"
