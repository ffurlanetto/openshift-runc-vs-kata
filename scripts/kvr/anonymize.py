"""Anonymisation de tout ce que le banc écrit (preuves, observations, campaign.json).

Le dépôt est public : aucune donnée permettant d'identifier ou de cartographier l'infrastructure ne doit
y entrer. Remplacements stables (même valeur → même pseudonyme, d'une campagne à l'autre) :

- valeurs connues de la cible : URL et hôte de l'API server, domaine du cluster, contexte kube, noms de
  nœuds, hôtes des miroirs de registre ;
- adresses IPv4 / IPv6 → 192.0.2.N / 2001:db8::N (plages réservées à la documentation) ;
- adresses e-mail ;
- noms DNS d'au moins 3 niveaux hors domaines publics connus (registres, kubernetes.io…).

La table de correspondance (`.kvr-private/anonymization-map.json`, ignorée par git) reste sur le poste de
l'opérateur : elle permet de relire localement les preuves avec les vrais noms. Ne jamais la commiter.

`find_leaks()` sert de dernier filet : à la fin d'une campagne et avant un commit (scripts/check_public.py).
"""

from __future__ import annotations

import ipaddress
import json
import re
from pathlib import Path
from urllib.parse import urlparse

# Domaines publics dont la présence ne révèle rien de l'infrastructure (registres, API Kubernetes, projets).
PUBLIC_SUFFIXES = (
    "kubernetes.io", "k8s.io", "x-k8s.io", "openshift.io", "openshift.com", "redhat.com", "redhat.io",
    "katacontainers.io", "kyverno.io", "docker.io", "docker.com", "quay.io", "ghcr.io", "gcr.io", "github.com",
    "githubusercontent.com", "github.io", "cncf.io", "cri-o.io", "ovn.org", "golang.org", "python.org",
    "pypi.org", "pythonhosted.org", "fedoraproject.org", "centos.org", "ubuntu.com", "debian.org",
    "alpinelinux.org", "example.com", "example.org", "example.invalid", "cluster.example", "cluster.local",
    "crc.testing", "nip.io", "hashicorp.com", "cyberark.com", "conjur.org", "min.io", "amazonaws.com",
    "anthropic.com", "claude.com", "jenkins.io", "kvr.local",
)
KEEP_IPS = {"0.0.0.0", "127.0.0.1", "255.255.255.255"}
DOC_NET4 = ipaddress.ip_network("192.0.2.0/24")

RE_IPV4 = re.compile(r"(?<![\w.:-])((?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3})(?![\w.-]*\d)")
RE_IPV6 = re.compile(r"(?<![\w:.])([0-9a-fA-F]{0,4}(?::[0-9a-fA-F]{0,4}){2,7}(?:/\d{1,3})?)(?![\w:.])")
RE_MAC = re.compile(r"(?<![\w:])((?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})(?![\w:])")
RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
RE_FQDN = re.compile(r"(?<![\w.@/-])((?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.){2,}[a-z]{2,24})(?![\w-])", re.I)


FILE_EXT = {"json", "yaml", "yml", "py", "md", "txt", "sh", "j2", "html", "log", "toml", "lock", "cfg", "conf", "ko",
            "xz", "gz", "tar", "js", "css", "tmpl", "csv", "xml", "ini", "pem", "crt", "service", "socket", "so"}


def _not_a_host(cand: str) -> bool:
    """Noms de fichiers (result.schema.json) et chemins de champs (RuntimeClass.overhead.podFixed) : pas des hôtes.
    Les vrais noms du cluster, eux, sont couverts par la table exacte (learn_target), majuscules comprises."""
    return cand.rsplit(".", 1)[-1].lower() in FILE_EXT or cand != cand.lower()


def _public(host: str) -> bool:
    h = host.lower().rstrip(".")
    if h.endswith(".svc") or ".svc." in h:  # noms de services internes au cluster (génériques)
        return True
    return any(h == s or h.endswith("." + s) for s in PUBLIC_SUFFIXES)


def _is_ipv6(s: str) -> bool:
    try:
        ipaddress.IPv6Address(s.split("/")[0])
        return s.count(":") >= 3  # évite les horodatages hh:mm:ss
    except ValueError:
        return False


class Anonymizer:
    def __init__(self, map_path: Path, enabled: bool = True) -> None:
        self.enabled = enabled
        self.map_path = map_path
        self.map: dict[str, dict[str, str]] = {"exact": {}, "ip": {}, "host": {}, "email": {}, "mac": {}}
        if map_path.exists():
            self.map.update(json.loads(map_path.read_text()))
        self._exact_re: re.Pattern | None = None

    # ---- table de correspondance
    def _pseudo(self, kind: str, value: str, prefix: str) -> str:
        table = self.map.setdefault(kind, {})
        if value not in table:
            n = 1 + sum(1 for v in table.values() if v.startswith(prefix))
            table[value] = f"{prefix}{n}"
        return table[value]

    def save(self) -> None:
        if not self.enabled:
            return
        self.map_path.parent.mkdir(parents=True, exist_ok=True)
        self.map_path.write_text(json.dumps(self.map, indent=2, ensure_ascii=False, sort_keys=True))
        try:
            self.map_path.chmod(0o600)
        except OSError:
            pass

    def learn_target(self, target: dict, fingerprint: dict | None = None) -> None:
        """Enregistre les valeurs connues de la cible, remplacées en priorité et quelle que soit leur forme."""
        if not self.enabled:
            return
        api = (fingerprint or {}).get("api_server") or target.get("api_server") or ""
        host = urlparse(api).hostname or ""
        if host and not _public(host) and not _is_ip(host):
            self.map["exact"].setdefault(host, "api.cluster.example")
            parts = host.split(".")
            if len(parts) > 2 and parts[0] == "api":
                self.map["exact"].setdefault(".".join(parts[1:]), "cluster.example")
        ctx = target.get("context")
        if ctx and ctx not in self.map["exact"]:
            self._pseudo("exact", ctx, "contexte-")
        for n in (fingerprint or {}).get("nodes", []):
            name = n.get("name")
            if name and name not in self.map["exact"] and name not in ("crc",):
                self._pseudo("exact", name, "noeud-")
        for m in (target.get("registry") or {}).get("mirrors", []):
            mh = str(m.get("to", "")).split("/")[0].split(":")[0]
            if mh and not _public(mh) and not _is_ip(mh) and mh not in self.map["exact"]:
                self._pseudo("exact", mh, "miroir-").__str__()
                self.map["exact"][mh] = self.map["exact"][mh] + ".example.invalid"
        self._exact_re = None
        self.save()

    # ---- remplacement
    def _exact_pattern(self) -> re.Pattern | None:
        if self._exact_re is None and self.map["exact"]:
            keys = sorted(self.map["exact"], key=len, reverse=True)
            self._exact_re = re.compile(r"(?<![\w-])(" + "|".join(re.escape(k) for k in keys) + r")(?![\w-])")
        return self._exact_re

    def text(self, s: str) -> str:
        if not self.enabled or not s:
            return s
        pat = self._exact_pattern()
        if pat:
            s = pat.sub(lambda m: self.map["exact"][m.group(1)], s)

        def ip4(m):
            v = m.group(1)
            if v in KEEP_IPS or ipaddress.ip_address(v) in DOC_NET4:
                return v
            return self._pseudo("ip", v, "192.0.2.") if len(self.map["ip"]) < 250 else "192.0.2.0"

        def ip6(m):
            v = m.group(1)
            if not _is_ipv6(v) or v.split("/")[0] in ("::1", "::"):
                return v
            return self._pseudo("ip", v, "2001:db8::")

        def host(m):
            v = m.group(1)
            if _public(v) or _not_a_host(v) or re.fullmatch(r"[\d.]+", v):
                return v
            return self._pseudo("host", v.lower(), "hote-") + ".example.invalid"

        s = RE_MAC.sub(lambda m: m.group(1) if m.group(1).lower().startswith("02:00:5e")
                       else "02:00:5e:00:" + f"{int(self._pseudo('mac', m.group(1).lower(), 'mac-')[4:]) // 256:02x}:"
                       f"{int(self._pseudo('mac', m.group(1).lower(), 'mac-')[4:]) % 256:02x}", s)
        s = RE_IPV4.sub(ip4, s)
        s = RE_IPV6.sub(ip6, s)
        s = RE_EMAIL.sub(lambda m: m.group(0) if m.group(0).endswith(("@127.0.0.1", "@localhost"))
                         else self._pseudo("email", m.group(0), "personne-") + "@example.invalid", s)
        s = RE_FQDN.sub(host, s)
        return s

    def obj(self, o):
        """Anonymise récursivement une structure JSON (clés comprises : noms de nœuds en clé, par ex.)."""
        if isinstance(o, str):
            return self.text(o)
        if isinstance(o, list):
            return [self.obj(v) for v in o]
        if isinstance(o, dict):
            return {self.text(k) if isinstance(k, str) else k: self.obj(v) for k, v in o.items()}
        return o


def _is_ip(s: str) -> bool:
    try:
        ipaddress.ip_address(s)
        return True
    except ValueError:
        return False


def find_leaks(text: str, known: dict | None = None) -> list[str]:
    """Ce qui ressemble encore à une donnée d'infrastructure. `known` : table de correspondance locale
    (toute valeur d'origine retrouvée telle quelle est une fuite certaine)."""
    leaks = []
    for v in RE_IPV4.findall(text):
        if v not in KEEP_IPS and ipaddress.ip_address(v) not in DOC_NET4:
            leaks.append(f"IP {v}")
    for v in RE_IPV6.findall(text):
        if _is_ipv6(v) and not v.lower().startswith("2001:db8:") and v.split("/")[0] not in ("::1", "::"):
            leaks.append(f"IPv6 {v}")
    for v in RE_MAC.findall(text):
        if not v.lower().startswith("02:00:5e"):
            leaks.append(f"MAC {v}")
    for v in RE_EMAIL.findall(text):
        if not v.endswith(("@example.invalid", "@127.0.0.1", "@localhost")):
            leaks.append(f"e-mail {v}")
    for v in RE_FQDN.findall(text):
        if not _public(v) and not _not_a_host(v):
            leaks.append(f"nom DNS {v}")
    for kind in ("exact", "ip", "host", "email", "mac"):
        for original in (known or {}).get(kind, {}):
            if len(original) >= 4 and re.search(r"(?<![\w-])" + re.escape(original) + r"(?![\w-])", text):
                leaks.append(f"valeur connue ({kind}) {original}")
    return sorted(set(leaks))
