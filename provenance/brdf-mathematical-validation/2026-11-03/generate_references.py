"""Independent 60-digit equation evaluation plus pinned external C++ checks.

No SpectralBridge imports. Requires mpmath only for fixture regeneration, not
runtime/tests. External source remains in /private/tmp, identified by URL/hash.
"""

import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, "/private/tmp/p166-libs")
import mpmath as mp  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
mp.mp.dps = 60


def reference(solar, view, azimuth, shape, height):
    """Literal scalar published equations, using arbitrary precision arithmetic."""
    s, v, phi = [mp.mpf(str(x)) * mp.pi / 180 for x in (solar, view, azimuth)]
    br, hb = mp.mpf(str(shape)), mp.mpf(str(height))
    phase = mp.acos(
        max(-1, min(1, mp.cos(s) * mp.cos(v) + mp.sin(s) * mp.sin(v) * mp.cos(phi)))
    )
    ross = ((mp.pi / 2 - phase) * mp.cos(phase) + mp.sin(phase)) / (
        mp.cos(s) + mp.cos(v)
    ) - mp.pi / 4
    sp, vp = mp.atan(br * mp.tan(s)), mp.atan(br * mp.tan(v))
    ts, tv = mp.tan(sp), mp.tan(vp)
    ss, sv = 1 / mp.cos(sp), 1 / mp.cos(vp)
    d2 = max(0, ts**2 + tv**2 - 2 * ts * tv * mp.cos(phi))
    c = min(1, hb * mp.sqrt(d2 + (ts * tv * mp.sin(phi)) ** 2) / (ss + sv))
    t = mp.acos(c)
    overlap = (t - mp.sin(t) * mp.cos(t)) * (ss + sv) / mp.pi
    phase_p = mp.cos(sp) * mp.cos(vp) + mp.sin(sp) * mp.sin(vp) * mp.cos(phi)
    sparse = overlap - ss - sv + (1 + phase_p) * ss * sv / 2
    dense = (1 + phase_p) * ss * sv / (ss + sv - overlap) - 2
    return dict(
        RossThick=float(ross), LiDenseR=float(dense), LiSparseReciprocal=float(sparse)
    )


def main():
    rows = []
    zeniths = [0, 5, 10, 30, 45, 60, 80, 89, 89.999]
    for s, v, phi, br in itertools.product(
        zeniths, zeniths, [0, 45, 90, 135, 180], [1, 2.5, 10]
    ):
        rows.append(
            dict(
                solar_deg=s,
                view_deg=v,
                relative_deg=phi,
                b_r=br,
                h_b=2,
                **reference(s, v, phi, br, 2),
            )
        )
    for s, v, phi, br, hb in [
        (30, 30, 1e-10, 10, 2),
        (1e-8, 1e-8, 45, 2.5, 2),
        (30, 30.00000001, 0, 10, 0.5),
        (0, 53.13010235415598, 0, 1, 2),
        (45, 60, 135, 2.5, 3),
    ]:
        rows.append(
            dict(
                solar_deg=s,
                view_deg=v,
                relative_deg=phi,
                b_r=br,
                h_b=hb,
                **reference(s, v, phi, br, hb),
            )
        )
    source = Path("/private/tmp/p166_RossLi.cpp")
    assert (
        hashlib.sha256(source.read_bytes()).hexdigest()
        == "a7d5c4bd3e7641c81c20fbf3ff64c6c8a00baab0284b2dedbf82b282d1abe4ae"
    ), "External reference revision changed"
    text = source.read_text()
    # Execute the upstream functions unchanged. Its LiDense is NONreciprocal:
    # convert its output to the reciprocal dense equation, rather than silently
    # treating the two variants as interchangeable reference values.
    core = text[
        text.index("struct Angles {") : text.index(
            "/** Helper function for getting the BRDF coefficients"
        )
    ]
    harness = (
        "#include <cmath>\n#include <iostream>\n#include <iomanip>\n"
        + core
        + """
int main() {
  double s,v,p,br,hb;
  while (std::cin >> s >> v >> p >> br >> hb) {
    Angles a(std::cos(s),std::cos(v),p);
    double sec_s = std::hypot(1.0,br*std::tan(s));
    std::cout << std::setprecision(17) << RossThick(a) << " "
              << (LiDense(a,br,hb)+2.0)*sec_s-2.0 << "\\n";
  }
}
"""
    )
    cpp = Path("/private/tmp/p166_reference.cpp")
    cpp.write_text(harness)
    subprocess.run(
        ["c++", "-std=c++17", "-O2", str(cpp), "-o", "/private/tmp/p166_reference"],
        check=True,
    )
    subset = [r for r in rows if max(r["solar_deg"], r["view_deg"]) <= 80][:]
    import math

    lines = [
        " ".join(
            str(x)
            for x in [
                math.radians(r["solar_deg"]),
                math.radians(r["view_deg"]),
                math.radians(r["relative_deg"]),
                r["b_r"],
                r["h_b"],
            ]
        )
        for r in subset
    ]
    output = subprocess.check_output(
        ["/private/tmp/p166_reference"], input="\n".join(lines), text=True
    )
    max_error = [0.0, 0.0]
    for row, result in zip(subset, output.splitlines(), strict=True):
        actual = [float(x) for x in result.split()]
        for i, key in enumerate(["RossThick", "LiDenseR"]):
            max_error[i] = max(max_error[i], abs(actual[i] - row[key]))
    record = dict(
        method="60-digit scalar published equations, independent of package; pinned DIRSIG C++ cross-check of Ross and transformed nonreciprocal dense",
        mpmath_version=mp.__version__,
        references=["MODIS ATBD v5 Eqs 38-44", "Zhang et al. 2018 Eqs 3-11"],
        independent_cpp=dict(
            url="https://dirsig-gitlab.cis.rit.edu/dirsig_public/dirsig-sdk/-/blob/1.2.5/lib/brdf/RossLi.cpp",
            sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            rows=len(subset),
            max_absolute_errors=dict(zip(["RossThick", "LiDenseR"], max_error)),
            dense_conversion="(nonreciprocal_dense + 2) * sec(transformed_solar_zenith) - 2",
        ),
        rows=rows,
    )
    target = ROOT / "tests/data/brdf/published_equation_references.json"
    target.write_text(json.dumps(record, indent=2) + "\n")
    print(len(rows), "high-precision cases; C++ max errors:", max_error)


if __name__ == "__main__":
    main()
