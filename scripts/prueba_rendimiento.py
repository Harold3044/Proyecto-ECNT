"""Prueba de rendimiento básica de la API (lectura concurrente, uso típico de la EPS).

Uso:  python scripts/prueba_rendimiento.py --url http://127.0.0.1:8000 --peticiones 200 --concurrencia 10
Resultados en reports/rendimiento.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from ecnt_core.config import ROOT


def bench(url: str, path: str, headers: dict, n: int, conc: int) -> dict:
    def one(_):
        t = time.perf_counter()
        r = requests.get(url + path, headers=headers, timeout=60)
        return time.perf_counter() - t, r.status_code

    t0 = time.perf_counter()
    with ThreadPoolExecutor(conc) as ex:
        res = list(ex.map(one, range(n)))
    total = time.perf_counter() - t0
    lat = sorted(x[0] * 1000 for x in res)
    ok = sum(1 for _, c in res if c == 200)
    return {"endpoint": path, "peticiones": n, "concurrencia": conc, "exitosas": ok,
            "media_ms": round(statistics.mean(lat), 1), "p50_ms": round(lat[len(lat) // 2], 1),
            "p95_ms": round(lat[int(len(lat) * 0.95) - 1], 1), "max_ms": round(lat[-1], 1),
            "peticiones_por_s": round(n / total, 1)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--peticiones", type=int, default=200)
    ap.add_argument("--concurrencia", type=int, default=10)
    ap.add_argument("--usuario", default="eps@ecnt.local")
    ap.add_argument("--clave", default="Eps2026!")
    a = ap.parse_args()
    t = time.perf_counter()
    tok = requests.post(f"{a.url}/auth/login", data={"username": a.usuario, "password": a.clave}, timeout=30).json()
    login_ms = (time.perf_counter() - t) * 1000
    h = {"Authorization": f"Bearer {tok['access_token']}"}
    div = requests.get(f"{a.url}/territories", headers=h, timeout=60).json()[0]["divipola"]
    results = [bench(a.url, p, h, a.peticiones, a.concurrencia) for p in
               ("/health", "/dashboard", "/territories?con_determinantes=true", f"/territories/{div}", "/alerts")]
    out = {"url": a.url, "login_ms": round(login_ms, 1), "resultados": results}
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "rendimiento.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), "utf-8")
    print(f"login: {login_ms:.0f} ms")
    for r in results:
        print(f"{r['endpoint']:<40} ok {r['exitosas']}/{r['peticiones']}  p50 {r['p50_ms']:>7} ms  "
              f"p95 {r['p95_ms']:>7} ms  {r['peticiones_por_s']:>6} req/s")


if __name__ == "__main__":
    main()
