"""Deterministic citation canonicalizer: the same law is always cited the same way,
whatever wording the source or the model used ("Civil Code section 1947.12",
"Cal. Civ. Code §1947.12" -> "Cal. Civ. Code § 1947.12")."""

import re

CODE_NAMES = [
    # (pattern, canonical prefix)
    (r"(?:Cal(?:ifornia)?\.?\s+)?Civ(?:il)?\.?\s+Code", "Cal. Civ. Code"),
    (r"(?:Cal(?:ifornia)?\.?\s+)?Gov(?:ernment|t)?\.?\s+Code", "Cal. Gov. Code"),
    (r"(?:Cal(?:ifornia)?\.?\s+)?Bus(?:iness)?\.?\s*(?:&|and)\s*Prof(?:essions)?\.?\s+Code", "Cal. Bus. & Prof. Code"),
    (r"(?:Cal(?:ifornia)?\.?\s+)?Code\s+(?:of\s+)?Regs?\.?|C\.C\.R\.", "Cal. Code Regs."),
    (r"N\.?\s?J\.?\s?S\.?\s?A\.?|N\.J\.\s*Stat\.?\s*Ann\.?|New Jersey Statutes(?: Annotated)?", "N.J.S.A."),
    (r"(?:M\.?\s?G\.?\s?L\.?|G\.\s?L\.|Mass(?:achusetts)?\.?\s+Gen(?:eral)?\.?\s+Laws|General Laws)", "M.G.L."),
    (r"(?:San Francisco|S\.?\s?F\.?)\s+Admin(?:istrative)?\.?\s+Code", "S.F. Admin. Code"),
    (r"L\.?\s?A\.?\s?M\.?\s?C\.?|Los Angeles Municipal Code", "L.A.M.C."),
    (r"San Diego Mun(?:icipal|\.)?\s+Code|SDMC", "San Diego Mun. Code"),
    (r"Berkeley Mun(?:icipal|\.)?\s+Code|BMC", "Berkeley Mun. Code"),
    (r"Oakland Mun(?:icipal|\.)?\s+Code|O\.\s?M\.\s?C\.|OMC", "Oakland Mun. Code"),
    (r"Santa Ana Mun(?:icipal|\.)?\s+Code", "Santa Ana Mun. Code"),
    (r"Jersey City (?:Mun(?:icipal|\.)?\s+)?Code", "Jersey City Code"),
    (r"Hoboken (?:City |Mun(?:icipal|\.)?\s+)?Code", "Hoboken Code"),
    (r"Newark(?:,\s*NJ)? (?:Mun(?:icipal|\.)?\s+)?Code", "Newark Code"),
    (r"Cambridge Mun(?:icipal|\.)?\s+Code", "Cambridge Mun. Code"),
    (r"Boston Mun(?:icipal|\.)?\s+Code|CBC", "Boston Mun. Code"),
]


def canon_citation(c: str) -> str:
    s = re.sub(r"\s+", " ", c.strip())
    for pat, canon in CODE_NAMES:
        s = re.sub(rf"^(?:{pat})(?=[\s,§]|$)", canon, s, flags=re.I)
        s = re.sub(rf"(?<=;\s)(?:{pat})(?=[\s,§]|$)", canon, s, flags=re.I)
    # Section words -> §, consistent spacing.
    s = re.sub(r"\b(?:Sections|Secs\.)\s+", "§§ ", s, flags=re.I)
    s = re.sub(r"\b(?:Section|Sec\.)\s+", "§ ", s, flags=re.I)
    s = re.sub(r"§\s*§", "§§", s)
    s = re.sub(r"(§§?)\s*(?=\S)", r"\1 ", s)
    s = re.sub(r"^N\.J\.S\.A\. §+ ", "N.J.S.A. ", s)  # N.J.S.A. cites take no section sign
    if s.startswith("M.G.L."):
        # "M.G.L. ch. 186 § 15B" / "c.186, §15B" -> "M.G.L. c. 186, § 15B"
        s = re.sub(r"\b(?:ch(?:apter)?\.?|c\.)\s*(\d+[A-Z]?)\s*,?\s*(§)", r"c. \1, \2", s)
        s = re.sub(r"\b(?:ch(?:apter)?\.?|c\.)\s*(\d+[A-Z]?)\b", r"c. \1", s)
    else:
        s = re.sub(r"\b(?:chapter|chap\.)\s*(?=\d)", "ch. ", s, flags=re.I)
    return s.strip(" ,;")


if __name__ == "__main__":
    for t in ["Civil Code section 1947.12", "Cal. Civ. Code §1947.12", "California Civil Code Sec. 1950.5",
              "NJSA 46:8-21.2", "N.J. Stat. Ann. § 2A:18-61.1", "G.L. c.186, §15B", "Mass. Gen. Laws ch. 40P, § 4",
              "San Francisco Administrative Code Section 37.9", "LAMC § 151.06", "Berkeley Municipal Code ch. 13.76",
              "M.G.L. c. 151B, § 4(10)", "P.L.2026, c.43", "Mass. S.2983", "Hoboken Code ch. 158, Art. II"]:
        print(f"{t!r:55} -> {canon_citation(t)!r}")
