"""VOL-01 : matrice de base d'un backend de stockage (ici : local, StorageClass par défaut ou paramétrée).

PVC RWO en mode Filesystem, pod restreint (UID arbitraire sur OpenShift) :
écriture d'un fichier de 64 MiB et d'une arborescence de petits fichiers (lien symbolique, lien dur,
renommage), `sync`, empreinte globale ; suppression du pod, nouveau pod sur la même PVC, relecture.
Le type de montage vu dans le conteneur (virtio-fs avec Kata) est relevé.
"""

import time

from kvr import storage

META = {"id": "VOL-01", "category": "VOL", "aspect": "FUN", "priority": "P1",
        "title": "Stockage : montage, écriture, persistance (backend local)", "runs": 3,
        "params": {"storage_class": "", "size_mib": 64}}

WRITE = r"""
set -e
cd /data
t0=$(date +%s%N)
dd if=/dev/urandom of=big.bin bs=1M count={size} status=none
sync
t1=$(date +%s%N)
mkdir -p tree/a/b tree/c
for i in $(seq 1 100); do echo "fichier $i" > tree/a/b/f$i.txt; done
for i in $(seq 1 50); do echo "autre $i" > tree/c/g$i.txt; done
echo contenu > tree/orig.txt && ln -s orig.txt tree/link.txt && ln tree/orig.txt tree/hard.txt
echo provisoire > tree/tmp.txt && mv tree/tmp.txt tree/renamed.txt
sync
echo "write_ns=$((t1 - t0))"
"""

INFO = r"""
echo "owner=$(stat -c '%u:%g:%a' /data) id=$(id -u):$(id -g) groups=$(id -G | tr ' ' ,)"
awk '$2 == "/data" {print "mount=" $1 " " $3}' /proc/mounts
"""

DIGEST = r"""
cd /data
{ sha256sum big.bin tree/a/b/f*.txt tree/c/g*.txt tree/orig.txt tree/hard.txt tree/renamed.txt;
  readlink tree/link.txt; stat -c '%h' tree/orig.txt; } | sha256sum | cut -c1-64
""" + INFO


def run(ctx):
    sc = storage.storage_class(ctx, "local")
    size = int(ctx.params["size_mib"])
    t0 = time.perf_counter()
    ctx.apply_template("pvc-pod.yaml.j2", pvc="data", storage_class=sc["name"], name="writer")
    ctx.wait("pod/writer", timeout_s=300)
    ctx.metric("pod_ready_with_pvc", round(time.perf_counter() - t0, 2), "s", "lower")

    rc, out, err = ctx.exec("writer", ["sh", "-c", WRITE.replace("{size}", str(size))], timeout_s=600)
    if rc != 0:
        _, info, _ = ctx.exec("writer", ["sh", "-c", INFO])
        ctx.evidence("write-error.txt", f"rc={rc}\n{out}\n{err}\n{info}")
        ctx.observe(f"{ctx.runtime} : écriture impossible sur {sc['name']} ({sc['provisioner']}) : "
                    f"{err.strip().splitlines()[-1][:160] if err.strip() else ''} ; {info.strip()}")
        return "FAIL"
    write_ns = int(out.split("write_ns=")[1].split()[0])
    _, d1, _ = ctx.exec("writer", ["sh", "-c", DIGEST])
    ctx.oc("delete", "pod", "writer", "-n", ctx.namespace, "--wait=true")
    ctx.apply_template("pvc-pod.yaml.j2", pvc="data", create_pvc=False, name="reader")
    ctx.wait("pod/reader", timeout_s=300)
    _, d2, _ = ctx.exec("reader", ["sh", "-c", DIGEST])
    ctx.evidence("digests.txt", f"storage_class={sc}\nwriter:\n{d1}\nreader:\n{d2}")

    same = d1.split()[0] == d2.split()[0] if d1.split() and d2.split() else False
    info = dict(l.split("=", 1) for l in d1.splitlines()[1:] if "=" in l)
    mbps = round(size / (write_ns / 1e9), 1)
    ctx.metric("write_seq_with_sync", mbps, "MB/s", "higher")
    ctx.metric("data_persisted", int(same), "bool", "higher")
    ctx.observe(f"{ctx.runtime} : {sc['name']} ({sc['provisioner']}), montage vu dans le conteneur "
                f"« {info.get('mount', '?')} » ; écriture {size} MiB + sync {mbps} MB/s ; données "
                f"{'identiques après recréation du pod' if same else 'DIFFÉRENTES après recréation du pod'} ; "
                f"{info.get('owner', '')} {info.get('id', '')}".strip())
    return "PASS" if same else "FAIL"
