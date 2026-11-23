"""POL-15 : un pod peut-il dépasser sa limite CPU à l'exécution ?

Pod limité à `cpu_limit`, qui lance `threads` boucles actives pendant `duration_s`. On mesure la
consommation réelle via le cgroup vu du conteneur (cpu.stat usage_usec), et le nombre de CPU visibles.
Avec kata, le cgroup mesuré est celui de la VM invitée : la mesure est complétée par la limite de vCPU.
"""

META = {"id": "POL-15", "category": "POL", "aspect": "FUN", "priority": "P1",
        "title": "Dépassement de la limite CPU à l'exécution", "runs": 3,
        "params": {"cpu_limit": "500m", "threads": 4, "duration_s": 15}}

SCRIPT = r"""
u() { grep usage_usec /sys/fs/cgroup/cpu.stat | cut -d' ' -f2; }
start=$(u); t0=$(date +%s%N)
for i in $(seq {threads}); do ( end=$((SECONDS+{duration})); while [ $SECONDS -lt $end ]; do :; done ) & done
wait
end=$(u); t1=$(date +%s%N)
echo "usage_usec=$((end-start)) wall_usec=$(( (t1-t0)/1000 )) nproc=$(nproc) cpu_max=$(cat /sys/fs/cgroup/cpu.max)"
"""


def run(ctx):
    p = ctx.params
    ctx.apply_template("policy-pod.yaml.j2", name="cpu", violations={"cpu_limit": p["cpu_limit"]})
    ctx.wait("pod/cpu", timeout_s=240)
    script = SCRIPT.replace("{threads}", str(p["threads"])).replace("{duration}", str(p["duration_s"]))
    rc, out, err = ctx.exec("cpu", ["bash", "-c", script], timeout_s=p["duration_s"] + 60)
    assert rc == 0, f"script CPU en échec : {err}"
    vals = dict(kv.split("=", 1) for kv in out.split() if "=" in kv)
    cores = int(vals["usage_usec"]) / int(vals["wall_usec"])
    limit = int(p["cpu_limit"].removesuffix("m")) / 1000 if p["cpu_limit"].endswith("m") else float(p["cpu_limit"])
    ctx.metric("effective_cpu_cores", round(cores, 3), "cores", "lower")
    ctx.metric("cpu_limit_ratio", round(cores / limit, 3), "ratio", "lower")
    ctx.metric("visible_cpus", int(vals["nproc"]), "count", "lower")
    ctx.evidence("cpu.txt", out)
    ctx.observe(f"limite {limit} cœur(s), consommé {cores:.2f} ; cpu.max={vals['cpu_max']} ; nproc={vals['nproc']}")
    return "PASS" if cores <= limit * 1.10 else "FAIL"
