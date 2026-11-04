"""Presentation-only spacing; never used for data or identifiers in artifacts."""

import re


def readable(value):
    protected = r"(https?://\S+|[0-9a-f]{20,}|\b[A-Za-z_]+(?:_[A-Za-z0-9]+)+\b|\b[A-Za-z_][A-Za-z0-9_]*\.(?:py|json|h5|csv|parquet)\b|\b\d+(?:\.\d+)?e[+-]?\d+\b|Float32|float32|H5|R10C|P\d+|SCS\+C|LiDenseR|LiSparseR|RossThick|MicaSense|FlexBRDF|LiSparseReciprocal)"
    pieces = re.split(protected, value)
    for i in range(0, len(pieces), 2):
        s = pieces[i]
        s = re.sub(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", s)
        s = re.sub(
            r"(BRDF|PFT|NEON|NDVI|ROI|OOF|RGB|UAV|AOP|OLS|UTC|CRS|CSV|API|FOV|MODIS|ATBD)(?=[a-z])",
            r"\1 ",
            s,
        )
        s = re.sub(r"([,:;])(?=[A-Za-z])", r"\1 ", s)
        s = re.sub(
            r"\b(A/B|C/D/E/F|C/D/E|C/D|A|B|C|D|E|F)(?=(?:use|are|has|have|factors|report|legacy|current|is|corrected))",
            r"\1 ",
            s,
        )
        s = s.replace("GoldhillMicaSense", "Goldhill MicaSense")
        pieces[i] = s
    # Insert spaces at the boundaries of protected tokens, without touching them.
    out = "".join(pieces)
    for token in (
        "Float32",
        "LiDenseR",
        "LiSparseR",
        "RossThick",
        "MicaSense",
        "FlexBRDF",
        "SCS+C",
        "H5",
        "R10C",
    ):
        out = re.sub(re.escape(token) + r"(?=[a-z])", token + " ", out)
    out = re.sub(r"(\.json)(?=(?:records|and))", r"\1 ", out)
    out = re.sub(r"(P\d+)(?=(?:found|ROI|evaluation))", r"\1 ", out)
    out = re.sub(r"(\d+e\d+)(?=because)", r"\1 ", out)
    out = re.sub(r"(A/B|C/D/E/F|C/D/E|C/D)(?=[a-z])", r"\1 ", out)
    out = out.replace("MODISATBD", "MODIS ATBD").replace(
        "November 3,2026", "November 3, 2026"
    )
    return out
