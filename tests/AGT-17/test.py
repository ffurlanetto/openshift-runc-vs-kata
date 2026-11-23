"""AGT-17 : abus de ressources par un agent — multiplication de processus (version bornée).

L'agent tente de créer `target` processus (sleep) pendant au plus 300 s. Borné volontairement : pas de
fork bomb infinie sur un nœud partagé. On mesure le plafond atteint et CE QUI l'a imposé :
- limite pids (fork refusé) ;
- limite mémoire du conteneur (le shell qui crée les processus est tué : OOM, code 137) ;
- rien (cible atteinte) : le nœud n'est protégé par aucune limite → FAIL.
runc : limites = cgroup du conteneur sur le nœud. kata : cgroup DANS l'invité (le nœud ne voit que la VM).

Le shell écrit sa progression dans un fichier avec des builtins (aucun fork) : si le shell est tué, la
progression reste lisible par un second exec.
"""

import time

META = {"id": "AGT-17", "category": "AGT", "aspect": "SEC", "priority": "P1", "agent_mode": "replay",
        "title": "Multiplication de processus (bornée)", "runs": 1, "warmup": False, "params": {"target": 6000}}

PROGRESS = "/tmp/kvr-agt17"
SLEEP_S = 600  # tués par le script lui-même (builtin kill, sans fork)
MAX_S = 90


def _cg(ctx, files: str) -> dict[str, str]:
    """Lit des fichiers cgroup du conteneur (cat est un fork : peut échouer si plus de pids)."""
    rc, out, _ = ctx.exec("probe", ["sh", "-c", f"cd /sys/fs/cgroup && for f in {files}; do "
                                                "printf '%s=' $f; tr '\\n' ' ' < $f 2>/dev/null || printf absent; echo; done"],
                          timeout_s=60)
    return dict(l.split("=", 1) for l in out.splitlines() if "=" in l) if rc == 0 else {}


def run(ctx):
    ctx.apply_template("probe-pod.yaml.j2")
    ctx.wait("pod/probe")
    before = _cg(ctx, "pids.max memory.max")
    target = int(ctx.params["target"])
    # Un seul bash ; arrêt dès qu'un fork échoue ($! inchangé). Progression écrite par builtin (pas de fork).
    # Borné à MAX_S : bash réessaie un fork refusé avec attente, la boucle ne doit pas durer indéfiniment.
    script = (f"pids=(); last=; i=0; for ((i=1; i<={target}; i++)); do sleep {SLEEP_S} & "
              f"if [ \"$!\" = \"$last\" ] || (( SECONDS > {MAX_S} )); then break; fi; last=$!; pids+=($!); "
              f"(( i % 25 == 0 )) && echo $i > {PROGRESS}; done 2>/dev/null; n=${{#pids[@]}}; "
              f"echo $n > {PROGRESS}; read pe < /sys/fs/cgroup/pids.events; echo \"DONE $n $SECONDS $pe\"; "
              "kill -9 \"${pids[@]}\" 2>/dev/null; wait 2>/dev/null; exit 0")
    t0 = time.perf_counter()
    rc, out, err = ctx.exec("probe", ["bash", "-c", script], timeout_s=300)
    elapsed = round(time.perf_counter() - t0, 1)
    time.sleep(5)
    pod = ctx.get("pod/probe")
    cs = (pod.get("status", {}).get("containerStatuses") or [{}])[0]
    term = cs.get("state", {}).get("terminated") or cs.get("lastState", {}).get("terminated") or {}
    container_killed = bool(term) or int(cs.get("restartCount", 0)) > 0
    after, progress = {}, None
    if not container_killed:
        after = _cg(ctx, "pids.events pids.peak memory.events")
        _, prog, _ = ctx.exec("probe", ["bash", "-c", f"read n < {PROGRESS} 2>/dev/null && echo $n"], timeout_s=60)
        progress = int(prog.strip()) if prog.strip().isdigit() else None
    done = next((int(l.split()[1]) for l in out.splitlines() if l.startswith("DONE ")), None)
    ctx.evidence("spawn.txt", f"exec rc={rc} en {elapsed}s\n{out[-1500:]}{err[-1500:]}\n"
                              f"cgroup avant : {before}\ncgroup après : {after}\nconteneur : {cs}")

    def field(key: str, name: str) -> int:
        ev = after.get(key, "").split()
        return int(ev[ev.index(name) + 1]) if name in ev else 0

    peak = after.get("pids.peak", "").strip()
    reached = done if done is not None else (int(peak) if peak.isdigit() else (progress or 0))
    done_line = next((l.split() for l in out.splitlines() if l.startswith("DONE ")), [])
    pids_refused = max(field("pids.events", "max"), int(done_line[4]) if len(done_line) > 4 and done_line[3] == "max" else 0)
    limit, mem = before.get("pids.max", "?").strip(), before.get("memory.max", "?").strip()
    if limit.isdigit():
        ctx.metric("pids_max_in_container", int(limit), "count", "lower")
    ctx.metric("container_killed", int(container_killed), "bool", "lower")
    if done is not None or progress is not None:
        ctx.metric("processes_reached", reached, "count", "lower")

    if container_killed:
        cause = (f"limite mémoire : conteneur tué en {elapsed}s (raison={term.get('reason', '?')}, "
                 f"code={term.get('exitCode', '?')}, memory.max={mem}) avant toute limite pids")
    elif pids_refused or (limit.isdigit() and reached >= int(limit) - 50):
        cause = (f"limite pids ({limit}) : {reached} processus, forks refusés="
                 f"{pids_refused if (after or done_line) else 'compteurs illisibles (plus de pids disponibles, exec rc=' + str(rc) + ')'}")
    elif reached >= target:
        cause = None
    else:
        cause = f"arrêt à {reached} sans cause identifiée (rc={rc})"
    ctx.observe(f"{ctx.runtime} : {target} processus tentés ; pids.max conteneur={limit} ; "
                f"{'contenu par ' + cause if cause else 'cible ATTEINTE : aucune limite'}")
    if cause is None:
        return "FAIL"
    return "PARTIAL" if "sans cause" in cause else "PASS"
