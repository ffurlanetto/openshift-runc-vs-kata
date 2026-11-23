"""POL-16 : un pod peut-il dépasser sa limite ephemeral-storage ?

Pod limité à `limit`, qui écrit `write_mib` dans son système de fichiers racine. Attendu : éviction
par le kubelet. Avec kata, l'écriture passe par le partage de fichiers de la VM : on vérifie que la
comptabilité et l'éviction fonctionnent toujours.
"""

import time

META = {"id": "POL-16", "category": "POL", "aspect": "FUN", "priority": "P1",
        "title": "Dépassement de la limite ephemeral-storage", "runs": 1,
        "params": {"limit": "100Mi", "write_mib": 300, "timeout_s": 240}}

POD = """
apiVersion: v1
kind: Pod
metadata: {{name: disk, namespace: {ns}}}
spec:
{rc}  restartPolicy: Never
  terminationGracePeriodSeconds: 0
  automountServiceAccountToken: false
{sel}  securityContext: {{runAsNonRoot: true{uid}, seccompProfile: {{type: RuntimeDefault}}}}
  containers:
    - name: main
      image: {image}
      command: ["bash", "-c", "head -c {mib}M /dev/zero > /tmp/fill; sync; sleep infinity"]
      resources:
        requests: {{cpu: 50m, memory: 32Mi, ephemeral-storage: 50Mi}}
        limits: {{cpu: 200m, memory: 128Mi, ephemeral-storage: {limit}}}
      securityContext: {{allowPrivilegeEscalation: false, capabilities: {{drop: ["ALL"]}}}}
"""


def run(ctx):
    p = ctx.params
    text = POD.format(
        ns=ctx.namespace, image=ctx.images["ubi_minimal"], mib=p["write_mib"], limit=p["limit"],
        rc=f"  runtimeClassName: {ctx.runtime_class}\n" if ctx.runtime_class else "",
        sel=f"  nodeSelector: {dict(ctx.node_selector)}\n" if ctx.node_selector else "",
        uid=", runAsUser: 1001" if ctx.platform == "kubernetes" else "")
    ctx.evidence("manifest-disk.yaml", text)
    ctx.cluster.oc("create", "-n", ctx.namespace, "-f", "-", input=text)
    t0 = time.perf_counter()
    evicted, phase, reason = False, None, None
    while time.perf_counter() - t0 < p["timeout_s"]:
        st = ctx.get("pod/disk").get("status", {})
        phase, reason = st.get("phase"), st.get("reason")
        if reason == "Evicted" or phase == "Failed":
            evicted = True
            break
        time.sleep(3)
    ctx.metric("evicted", int(evicted), "bool", "higher")
    if evicted:
        ctx.metric("time_to_eviction", round(time.perf_counter() - t0, 1), "s", "lower")
    ctx.observe(f"écrit {p['write_mib']} MiB pour une limite {p['limit']} : phase={phase} reason={reason}")
    return "PASS" if evicted else "FAIL"
