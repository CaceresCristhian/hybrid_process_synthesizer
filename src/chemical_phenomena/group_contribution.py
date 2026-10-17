"""
Predictive Molecular Property & Group-Contribution Estimator (Joback-Reid 1987 + Lee-Kesler + UNIFAC).
Estimates pure-component critical constants (Tb, Tm, Tc, Pc, Vc, omega), ideal-gas heat capacity
polynomials Cp(T) = C0 + C1*T + C2*T^2 + C3*T^3, standard formation enthalpies/Gibbs energies,
Antoine vapor pressure parameters, and UNIFAC subgroups directly from a SMILES string.
"""

import math
import re
from typing import Dict, List, Optional, Tuple
from src.database.chemical_db import (
    ChemicalSpecies,
    MicroScaleData,
    MacroScaleData,
    SystemScaleData,
)


# Joback & Reid (1987) Functional Group Contributions:
# Keys: group_name -> {
#   "Tb": K, "Tm": K, "Tc": dimensionless, "Pc": bar^-0.5, "Vc": cm^3/mol,
#   "Gf": kJ/mol, "Hf": kJ/mol,
#   "a": J/(mol K), "b": J/(mol K^2), "c": J/(mol K^3), "d": J/(mol K^4),
#   "Na": number of heavy/ring atoms in group
# }
JOBACK_GROUPS: Dict[str, Dict[str, float]] = {
    "-CH3":     {"Tb": 23.58, "Tm": -5.10,  "Tc": 0.0141, "Pc": -0.0012, "Vc": 65.0,  "Hf": -76.45,  "Gf": -43.96,  "a": 19.5,  "b": -0.00808, "c": 1.53e-4,  "d": -9.67e-8, "Na": 1},
    "-CH2-":    {"Tb": 22.88, "Tm": 11.27,  "Tc": 0.0189, "Pc": 0.0000,  "Vc": 56.0,  "Hf": -20.64,  "Gf": 8.42,    "a": -0.909,"b": 0.0950,   "c": -5.44e-5, "d": 1.19e-8,  "Na": 1},
    ">CH-":     {"Tb": 21.74, "Tm": 12.64,  "Tc": 0.0164, "Pc": 0.0020,  "Vc": 41.0,  "Hf": 29.89,   "Gf": 58.36,   "a": -23.0, "b": 0.204,    "c": -2.65e-4, "d": 1.20e-7,  "Na": 1},
    ">C<":      {"Tb": 18.25, "Tm": 46.43,  "Tc": 0.0067, "Pc": 0.0043,  "Vc": 27.0,  "Hf": 82.23,   "Gf": 116.02,  "a": -66.2, "b": 0.427,    "c": -6.41e-4, "d": 3.01e-7,  "Na": 1},
    "=CH2":     {"Tb": 18.18, "Tm": -4.32,  "Tc": 0.0113, "Pc": -0.0028, "Vc": 56.0,  "Hf": -9.63,   "Gf": 3.77,    "a": 23.6,  "b": -0.0381,  "c": 1.72e-4,  "d": -1.03e-7, "Na": 1},
    "=CH-":     {"Tb": 24.96, "Tm": 8.73,   "Tc": 0.0129, "Pc": -0.0006, "Vc": 46.0,  "Hf": 37.97,   "Gf": 48.53,   "a": -8.00, "b": 0.105,    "c": -9.63e-5, "d": 3.56e-8,  "Na": 1},
    "=C<":      {"Tb": 24.14, "Tm": 11.14,  "Tc": 0.0117, "Pc": 0.0011,  "Vc": 38.0,  "Hf": 83.99,   "Gf": 92.36,   "a": -28.1, "b": 0.208,    "c": -3.06e-4, "d": 1.46e-7,  "Na": 1},
    "ring-CH2-":{"Tb": 27.15, "Tm": 7.75,   "Tc": 0.0100, "Pc": 0.0025,  "Vc": 48.0,  "Hf": -26.80,  "Gf": -3.68,   "a": -6.03, "b": 0.0854,   "c": -8.00e-6, "d": -1.80e-8, "Na": 1},
    "ring=CH-": {"Tb": 26.73, "Tm": 8.13,   "Tc": 0.0082, "Pc": 0.0011,  "Vc": 41.0,  "Hf": 2.09,    "Gf": 11.30,   "a": -2.14, "b": 0.0574,   "c": -1.64e-6, "d": -1.59e-8, "Na": 1},
    "ring=C<":  {"Tb": 31.01, "Tm": 37.02,  "Tc": 0.0143, "Pc": 0.0008,  "Vc": 32.0,  "Hf": 46.43,   "Gf": 54.05,   "a": -8.25, "b": 0.101,    "c": -1.42e-4, "d": 6.78e-8,  "Na": 1},
    "-OH":      {"Tb": 92.88, "Tm": 44.45,  "Tc": 0.0741, "Pc": 0.0112,  "Vc": 28.0,  "Hf": -208.04, "Gf": -189.20, "a": 25.7,  "b": -0.0691,  "c": 1.77e-4,  "d": -9.88e-8, "Na": 1},
    "-OH(phenol)":{"Tb":76.34,"Tm": 82.83,  "Tc": 0.0240, "Pc": 0.0184,  "Vc": -25.0, "Hf": -221.65, "Gf": -197.37, "a": -2.81, "b": 0.111,    "c": -1.16e-4, "d": 4.94e-8,  "Na": 1},
    "-O-":      {"Tb": 22.42, "Tm": 22.23,  "Tc": 0.0168, "Pc": 0.0015,  "Vc": 18.0,  "Hf": -132.22, "Gf": -105.00, "a": 25.5,  "b": -0.0632,  "c": 1.11e-4,  "d": -5.48e-8, "Na": 1},
    ">C=O":     {"Tb": 76.75, "Tm": 61.20,  "Tc": 0.0380, "Pc": 0.0031,  "Vc": 62.0,  "Hf": -133.22, "Gf": -120.50, "a": 6.45,  "b": 0.0670,   "c": -3.57e-5, "d": 2.86e-9,  "Na": 2},
    "-CHO":     {"Tb": 72.24, "Tm": 36.90,  "Tc": 0.0379, "Pc": 0.0030,  "Vc": 82.0,  "Hf": -162.03, "Gf": -143.48, "a": 30.9,  "b": -0.0336,  "c": 1.60e-4,  "d": -9.88e-8, "Na": 2},
    "-COOH":    {"Tb": 169.09,"Tm": 155.50, "Tc": 0.0791, "Pc": 0.0077,  "Vc": 89.0,  "Hf": -426.72, "Gf": -387.87, "a": 24.1,  "b": 0.0427,   "c": 8.04e-5,  "d": -6.87e-8, "Na": 3},
    "-COO-":    {"Tb": 81.10, "Tm": 53.60,  "Tc": 0.0481, "Pc": 0.0005,  "Vc": 82.0,  "Hf": -337.92, "Gf": -301.95, "a": 24.5,  "b": 0.0402,   "c": 4.02e-5,  "d": -4.52e-8, "Na": 3},
    "-NH2":     {"Tb": 73.23, "Tm": 66.89,  "Tc": 0.0243, "Pc": 0.0109,  "Vc": 38.0,  "Hf": -22.02,  "Gf": 14.07,   "a": 26.9,  "b": -0.0412,  "c": 1.64e-4,  "d": -9.76e-8, "Na": 1},
    ">NH":      {"Tb": 50.17, "Tm": 52.66,  "Tc": 0.0295, "Pc": 0.0077,  "Vc": 35.0,  "Hf": 53.47,   "Gf": 89.39,   "a": -1.21, "b": 0.0762,   "c": -4.86e-5, "d": 1.05e-8,  "Na": 1},
    "-CN":      {"Tb": 125.66,"Tm": 59.89,  "Tc": 0.0496, "Pc": -0.0101, "Vc": 91.0,  "Hf": 88.43,   "Gf": 89.22,   "a": 36.5,  "b": -0.0733,  "c": 1.84e-4,  "d": -1.03e-7, "Na": 2},
    "-NO2":     {"Tb": 152.54,"Tm": 127.24, "Tc": 0.0437, "Pc": 0.0064,  "Vc": 91.0,  "Hf": -66.57,  "Gf": -16.83,  "a": 25.9,  "b": -0.00374, "c": 1.29e-4,  "d": -8.88e-8, "Na": 3},
    "-F":       {"Tb": -0.03, "Tm": -15.78, "Tc": 0.0111, "Pc": -0.0057, "Vc": 27.0,  "Hf": -251.92, "Gf": -247.19, "a": 26.5,  "b": -0.0913,  "c": 1.91e-4,  "d": -1.03e-7, "Na": 1},
    "-Cl":      {"Tb": 38.13, "Tm": 13.55,  "Tc": 0.0105, "Pc": -0.0049, "Vc": 58.0,  "Hf": -71.55,  "Gf": -64.31,  "a": 33.3,  "b": -0.0963,  "c": 1.87e-4,  "d": -9.96e-8, "Na": 1},
    "-Br":      {"Tb": 66.86, "Tm": 43.43,  "Tc": 0.0133, "Pc": 0.0057,  "Vc": 71.0,  "Hf": -29.48,  "Gf": -38.06,  "a": 28.6,  "b": -0.0649,  "c": 1.36e-4,  "d": -7.45e-8, "Na": 1},
    "-SH":      {"Tb": 63.56, "Tm": 20.09,  "Tc": 0.0031, "Pc": 0.0084,  "Vc": 63.0,  "Hf": -17.33,  "Gf": -22.99,  "a": 35.3,  "b": -0.0758,  "c": 1.85e-4,  "d": -1.03e-7, "Na": 1},
}

ATOMIC_WEIGHTS: Dict[str, float] = {
    "C": 12.011, "H": 1.008, "O": 15.999, "N": 14.007,
    "S": 32.06, "P": 30.974, "F": 18.998, "Cl": 35.45,
    "Br": 79.904, "I": 126.904, "Na": 22.990, "K": 39.098,
    "Ca": 40.078, "Mg": 24.305, "Si": 28.085,
}

PAULING_EN: Dict[str, float] = {
    "H": 2.20, "C": 2.55, "N": 3.04, "O": 3.44, "F": 3.98,
    "P": 2.19, "S": 2.58, "Cl": 3.16, "Br": 2.96, "I": 2.66,
}


class JobackPropertyEstimator:
    """
    Estimates pure-component thermodynamic, transport, and UNIFAC group properties
    from a SMILES string using Joback-Reid (1987) + Lee-Kesler correlations.
    """

    @classmethod
    def parse_smiles_groups(cls, smiles: str) -> Dict[str, int]:
        """
        Decomposes an organic SMILES string into Joback-Reid functional group counts.
        Handles linear/branched alkanes, alkenes, aromatics, alcohols, phenols, ketones,
        aldehydes, carboxylic acids, esters, ethers, amines, nitriles, nitro, thiols, and halides.
        """
        s = smiles.strip()
        groups: Dict[str, int] = {}

        def _add(g: str, count: int = 1):
            if count > 0:
                groups[g] = groups.get(g, 0) + count

        # Detect aromatic rings (lowercase 'c')
        n_arom_c = s.count("c")
        is_aromatic = n_arom_c >= 5

        # Strip explicit stereochemistry and ring digits for group pattern matching
        work = re.sub(r"[@/\\]", "", s)

        # 1. Carboxylic acid: C(=O)O or OC(=O) at terminus
        n_cooh = len(re.findall(r"C\(=O\)O(?![Ccn])|OC\(=O\)(?![Ccn])", work))
        if n_cooh:
            _add("-COOH", n_cooh)
            work = re.sub(r"C\(=O\)O(?![Ccn])|OC\(=O\)(?![Ccn])", "", work)

        # 2. Ester: C(=O)O followed by carbon
        n_coo = len(re.findall(r"C\(=O\)O|OC\(=O\)", work))
        if n_coo:
            _add("-COO-", n_coo)
            work = re.sub(r"C\(=O\)O|OC\(=O\)", "", work)

        # 3. Aldehyde: C=O at start/end
        n_cho = len(re.findall(r"^O=C|C=O$", work))
        if n_cho:
            _add("-CHO", n_cho)
            work = re.sub(r"^O=C|C=O$", "", work)

        # 4. Ketone: C(=O)
        n_co = len(re.findall(r"C\(=O\)", work))
        if n_co:
            _add(">C=O", n_co)
            work = re.sub(r"C\(=O\)", "", work)

        # 5. Nitrile: C#N
        n_cn = len(re.findall(r"C#N|N#C", work))
        if n_cn:
            _add("-CN", n_cn)
            work = re.sub(r"C#N|N#C", "", work)

        # 6. Nitro: [N+](=O)[O-] or N(=O)=O
        n_no2 = len(re.findall(r"\[N\+\]\(=O\)\[O-\]|N\(=O\)=O", work))
        if n_no2:
            _add("-NO2", n_no2)
            work = re.sub(r"\[N\+\]\(=O\)\[O-\]|N\(=O\)=O", "", work)

        # 7. Halogens & Thiols
        for sym, grp in [("Cl", "-Cl"), ("Br", "-Br"), ("F", "-F"), ("S", "-SH")]:
            cnt = len(re.findall(sym, work))
            if cnt:
                _add(grp, cnt)
                work = work.replace(sym, "")

        # 8. Hydroxyl (-OH / phenol) vs Ether (-O-)
        # Count remaining 'O'
        n_o = work.count("O")
        if n_o > 0:
            # Terminal O (at start/end or in parentheses (O)) -> -OH
            n_oh_term = len(re.findall(r"^O|O$|\(O\)", work))
            n_oh = max(1 if (n_o == 1 and ("O" == s[0] or "O" == s[-1] or "(O)" in s)) else 0, n_oh_term)
            n_oh = min(n_o, n_oh)
            n_ether = n_o - n_oh
            if n_oh > 0:
                if is_aromatic and len(re.findall(r"O", re.sub(r"c", "", s))) > 0 and "CC" not in s:
                    _add("-OH(phenol)", n_oh)
                else:
                    _add("-OH", n_oh)
            if n_ether > 0:
                _add("-O-", n_ether)

        # 9. Amines (-NH2 / >NH)
        n_n = work.count("N")
        if n_n > 0:
            n_nh2 = len(re.findall(r"^N|N$|\(N\)", work))
            n_nh2 = min(n_n, max(1 if n_n == 1 else 0, n_nh2))
            _add("-NH2", n_nh2)
            _add(">NH", n_n - n_nh2)

        # 10. Aromatic ring carbons
        if is_aromatic:
            # Substituted aromatic carbons have branches or attachments
            n_sub = max(0, len(re.findall(r"c\(|c[CNOF]|^[CNOF]c", s)))
            n_sub = min(n_arom_c, n_sub)
            _add("ring=C<", n_sub)
            _add("ring=CH-", max(0, n_arom_c - n_sub))

        # 11. Aliphatic carbons (count 'C' remaining in work)
        # Double bonds C=C
        n_dbl = work.count("=")
        n_aliph_c = work.count("C")
        if n_dbl > 0 and n_aliph_c >= 2 * n_dbl:
            _add("=CH2", min(2 * n_dbl, 1))
            _add("=CH-", max(0, 2 * n_dbl - 1))
            n_aliph_c -= 2 * n_dbl

        if n_aliph_c > 0:
            # Check if alicyclic ring (e.g., C1CCCCC1)
            is_alicyclic = (not is_aromatic) and bool(re.search(r"C1.*1", s))
            if is_alicyclic:
                _add("ring-CH2-", n_aliph_c)
            else:
                # Branching count via '(' around C
                n_branches = len(re.findall(r"\(C", work))
                if n_aliph_c == 1:
                    _add("-CH3", 1)
                elif n_aliph_c == 2:
                    # If attached to a polar group (-OH, -COOH, -NH2, etc.), one is -CH3 and one is -CH2-
                    has_polar = any(k in groups for k in ("-OH", "-COOH", "-CHO", "-NH2", "-Cl", "-Br", "-SH", "ring=C<"))
                    if has_polar:
                        _add("-CH3", 1)
                        _add("-CH2-", 1)
                    else:
                        _add("-CH3", 2)
                else:
                    n_ch3 = min(n_aliph_c, 2 + n_branches - (1 if any(k in groups for k in ("-OH", "-COOH", "-CHO", "-NH2", "ring=C<")) else 0))
                    n_ch3 = max(1, n_ch3)
                    rem = max(0, n_aliph_c - n_ch3)
                    n_ch = min(rem, n_branches)
                    n_ch2 = max(0, rem - n_ch)
                    _add("-CH3", n_ch3)
                    _add("-CH2-", n_ch2)
                    _add(">CH-", n_ch)

        if not groups:
            _add("-CH3", 2)
        return groups

    @classmethod
    def groups_to_unifac(cls, joback_groups: Dict[str, int]) -> Dict[str, int]:
        """Maps Joback functional groups to UNIFAC subgroup counts (compatible with src/chemical_phenomena/unifac.py)."""
        unifac: Dict[str, int] = {}
        mapping = {
            "-CH3": "CH3",
            "-CH2-": "CH2",
            ">CH-": "CH",
            ">C<": "C",
            "ring-CH2-": "CH2",
            "ring=CH-": "ACH",
            "ring=C<": "AC",
            "-OH": "OH",
            "-OH(phenol)": "ACOH",
            ">C=O": "CH3CO",
            "-CHO": "CHO",
            "-COOH": "COOH",
            "-COO-": "CH3COO",
        }
        for j_grp, cnt in joback_groups.items():
            u_grp = mapping.get(j_grp)
            if u_grp and cnt > 0:
                unifac[u_grp] = unifac.get(u_grp, 0) + cnt
        return unifac

    @classmethod
    def estimate_properties(
        cls,
        smiles: str,
        known_tb: Optional[float] = None,
        known_mw: Optional[float] = None,
    ) -> Dict[str, any]:
        """
        Computes Joback-Reid (1987) + Lee-Kesler properties from SMILES.
        If experimental normal boiling point `known_tb` [K] is provided, anchors Tc and omega to `known_tb`
        as recommended by Joback & Reid (reducing Tc error to < 1.5%).
        """
        groups = cls.parse_smiles_groups(smiles)

        sum_tb = sum(cnt * JOBACK_GROUPS[g]["Tb"] for g, cnt in groups.items())
        sum_tm = sum(cnt * JOBACK_GROUPS[g]["Tm"] for g, cnt in groups.items())
        sum_tc = sum(cnt * JOBACK_GROUPS[g]["Tc"] for g, cnt in groups.items())
        sum_pc = sum(cnt * JOBACK_GROUPS[g]["Pc"] for g, cnt in groups.items())
        sum_vc = sum(cnt * JOBACK_GROUPS[g]["Vc"] for g, cnt in groups.items())
        sum_hf = sum(cnt * JOBACK_GROUPS[g]["Hf"] for g, cnt in groups.items())
        sum_gf = sum(cnt * JOBACK_GROUPS[g]["Gf"] for g, cnt in groups.items())
        sum_a = sum(cnt * JOBACK_GROUPS[g]["a"] for g, cnt in groups.items())
        sum_b = sum(cnt * JOBACK_GROUPS[g]["b"] for g, cnt in groups.items())
        sum_c = sum(cnt * JOBACK_GROUPS[g]["c"] for g, cnt in groups.items())
        sum_d = sum(cnt * JOBACK_GROUPS[g]["d"] for g, cnt in groups.items())
        n_atoms = sum(cnt * JOBACK_GROUPS[g]["Na"] for g, cnt in groups.items())
        # Include approximate hydrogen count in total atoms N_A for Joback Pc formula
        n_total_atoms = max(3, int(n_atoms * 2.8))

        tb = float(known_tb) if (known_tb is not None and known_tb > 20.0) else float(198.2 + sum_tb)
        tm = float(max(50.0, 122.5 + sum_tm))

        # Joback Tc [K]: Tc = Tb / (0.584 + 0.965 * sum_Tc - (sum_Tc)^2)
        tc_denom = max(0.25, 0.584 + 0.965 * sum_tc - (sum_tc ** 2))
        tc = float(max(tb * 1.15, tb / tc_denom))

        # Joback Pc [bar -> Pa]: Pc [bar] = (0.113 + 0.0032 * N_A - sum_Pc)^(-2)
        pc_base = max(0.08, 0.113 + 0.0032 * n_total_atoms - sum_pc)
        pc_bar = float(max(5.0, min(250.0, pc_base ** (-2))))
        pc_pa = pc_bar * 1.0e5

        # Joback Vc [cm^3/mol -> m^3/kmol]: Vc = (17.5 + sum_Vc) / 1000
        vc_m3_kmol = float(max(0.040, (17.5 + sum_vc) / 1000.0))

        # Lee-Kesler (1975) acentric factor omega from (Tb, Tc, Pc)
        t_br = min(0.92, max(0.35, tb / tc))
        f0 = 5.92714 - (6.09648 / t_br) - 1.28862 * math.log(t_br) + 0.169347 * (t_br ** 6)
        f1 = 15.2518 - (15.6875 / t_br) - 13.4721 * math.log(t_br) + 0.43577 * (t_br ** 6)
        omega = float(max(-0.25, min(1.5, (-math.log(pc_bar / 1.01325) - f0) / max(1e-6, f1))))

        # Ideal-gas polynomial Cp(T) = C0 + C1*T + C2*T^2 + C3*T^3 [J/(mol K)]
        c0 = float(sum_a - 37.93)
        c1 = float(sum_b + 0.210)
        c2 = float(sum_c - 3.91e-4)
        c3 = float(sum_d + 2.06e-7)

        # Standard formation enthalpy & Gibbs free energy [kJ/mol]
        hf_298 = float(68.29 + sum_hf)
        gf_298 = float(53.88 + sum_gf)

        # Derive consistent Antoine coefficients [A, B, C] for log10(P_bar) = A - B / (T + C)
        # anchored at normal boiling point (Tb, 1.01325 bar) and critical point (Tc, Pc_bar)
        antoine_a, antoine_b, antoine_c = cls.derive_antoine_from_critical(tb, tc, pc_bar)

        return {
            "groups": groups,
            "unifac_subgroups": cls.groups_to_unifac(groups),
            "boiling_point": round(tb, 2),
            "melting_point": round(tm, 2),
            "critical_temperature": round(tc, 2),
            "critical_pressure": round(pc_pa, 1),
            "critical_volume": round(vc_m3_kmol, 4),
            "acentric_factor": round(omega, 4),
            "cp_constants": [round(c0, 3), round(c1, 5), round(c2, 8), round(c3, 11)],
            "hf_298_kJ_mol": round(hf_298, 2),
            "gf_298_kJ_mol": round(gf_298, 2),
            "antoine_coefficients": [round(antoine_a, 5), round(antoine_b, 3), round(antoine_c, 3)],
        }

    @staticmethod
    def derive_antoine_from_critical(tb: float, tc: float, pc_bar: float) -> List[float]:
        """
        Derives 3-parameter Antoine coefficients [A, B, C] for log10(P_bar) = A - B / (T + C)
        using Thomson's rule for C and anchoring exactly at (Tb, 1.01325 bar) and (Tc, Pc_bar).
        """
        tb_safe = max(20.0, float(tb))
        tc_safe = max(tb_safe + 15.0, float(tc))
        pc_safe = max(1.5, float(pc_bar))

        # Thomson /fishtine correlation for Antoine C parameter [K]
        c_val = -18.0 - 0.19 * max(0.0, tb_safe - 273.15)
        c_val = max(-120.0, min(0.0, c_val))
        if tb_safe + c_val <= 10.0:
            c_val = -0.1 * tb_safe

        y_b = math.log10(1.01325)
        y_c = math.log10(pc_safe)
        inv_tb = 1.0 / (tb_safe + c_val)
        inv_tc = 1.0 / (tc_safe + c_val)

        b_val = (y_c - y_b) / max(1e-9, inv_tb - inv_tc)
        a_val = y_b + b_val * inv_tb
        return [float(a_val), float(b_val), float(c_val)]

    @classmethod
    def build_species_from_smiles(
        cls,
        smiles: str,
        name: str = "Custom Species",
        species_id: Optional[str] = None,
        formula: str = "",
        known_tb: Optional[float] = None,
        known_mw: Optional[float] = None,
    ) -> ChemicalSpecies:
        """Creates a full ChemicalSpecies instance directly from a SMILES string."""
        props = cls.estimate_properties(smiles, known_tb=known_tb, known_mw=known_mw)
        sp_id = species_id or re.sub(r"[^a-z0-9_]", "_", name.lower()).strip("_") or "custom_species"

        # Approximate MW from SMILES if not provided
        mw = float(known_mw) if (known_mw and known_mw > 0) else max(16.0, sum(
            cnt * 14.0 for cnt in props["groups"].values()
        ))

        return ChemicalSpecies(
            id=sp_id,
            name=name,
            formula=formula or smiles,
            micro=MicroScaleData(
                molecular_weight=round(mw, 3),
                electronegativities={"C": 2.55, "H": 2.20, "O": 3.44},
                dipole_moment=1.2 if any("O" in g or "N" in g for g in props["groups"]) else 0.1,
                polarizability=round(mw * 0.12, 2),
                smiles=smiles,
            ),
            macro=MacroScaleData(
                boiling_point=props["boiling_point"],
                melting_point=props["melting_point"],
                critical_temperature=props["critical_temperature"],
                critical_pressure=props["critical_pressure"],
                critical_volume=props["critical_volume"],
                acentric_factor=props["acentric_factor"],
                cp_constants=props["cp_constants"],
            ),
            system=SystemScaleData(
                antoine_coefficients=props["antoine_coefficients"],
            ),
        )
