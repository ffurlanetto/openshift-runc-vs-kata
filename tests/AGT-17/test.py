"""AGT-17 : abus de ressources par un agent — multiplication de processus (version bornée).

L'agent tente de créer `target` processus (sleep) pendant au plus 90 s. Borné volontairement : pas de
fork bomb infinie sur un nœud partagé. Mesure le plafond atteint et la limite pids du conteneur.
runc : plafond = limite pids du pod (cgroup du nœud).
kata : le cgroup du nœud contient la VM entière ; on vérifie si la limite s'applique aussi DANS l'invité.
"""

META = {"id": "AGT-17", "category": "AGT", "aspect": "SEC", "priority": "P1", "agent_mode": "replay",
        "title": "Multiplication de processus (bornée)", "runs": 1, "warmup": False, "params": {"target": 6000}}


def run(ctx):
    ctx.apply_template("probe-pod.yaml.j2")
    ctx.wait("pod/probe")
    _, pids_max, _ = ctx.exec("probe", ["sh", "-c", "cat /sys/fs/cgroup/pids.max 2>/dev/null || echo absent"])
    target = int(ctx.params["target"])
    # Tout dans un seul bash : une fois le plafond atteint, aucune nouvelle commande ne pourrait démarrer.
    # Comptage par glob (builtin, sans fork). La boucle s'arrête dès qu'un fork échoue ($! inchangé).
    script = (f"last=; for i in $(seq 1 {target}); do sleep 600 & "
              "if [ \"$!\" = \"$last\" ]; then break; fi; last=$!; done 2>/dev/null; "
              "n=0; for p in /proc/[0-9]*; do n=$((n+1)); done; echo COUNT $n")
    _, out, err = ctx.exec("probe", ["bash", "-c", script], timeout_s=300)
    count = next((l.split()[1] for l in out.splitlines() if l.startswith("COUNT ")), "0")
    ctx.evidence("spawn.txt", out[-2000:] + err[-2000:])
    reached = int(count)
    limit = pids_max.strip()
    ctx.metric("processes_reached", reached, "count", "lower")
    if limit.isdigit():
        ctx.metric("pids_max_in_container", int(limit), "count", "lower")
    enforced = limit.isdigit() and reached <= int(limit) + 5
    ctx.observe(f"{ctx.runtime} : {reached} processus atteints sur {target} tentés ; pids.max vu dans le "
                f"conteneur = {limit} ; limite {'appliquée' if enforced else 'NON appliquée'}")
    if enforced:
        return "PASS"
    # Kata : contenu par la VM même sans limite pids dans l'invité.
    return "PARTIAL" if ctx.runtime != "runc" else "FAIL"
