
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any
import json
import argparse

# RFC 6996 private-use ASNs (16-bit + 32-bit ranges)
def _is_private_asn(asn: int) -> bool:
    return (64512 <= asn <= 65534) or (4200000000 <= asn <= 4294967294)

@dataclass(frozen=True)
class RouterConf:
    asn: int      # confederation identifier if sub_as != 0, else "real" AS
    sub_as: int   # member AS inside the confed; 0 => not in confed

    @property
    def in_confed(self) -> bool:
        return self.sub_as != 0

def _same_confed(r2: RouterConf, r3: RouterConf) -> bool:
    return r2.in_confed and r3.in_confed and (r2.asn == r3.asn)

def _session_type_r2_r3(r2: RouterConf, r3: RouterConf, is_external_peer_r3: bool) -> str:
    """
    Returns one of: "NONE", "IBGP", "CONFED_EBGP", "EBGP"
    Based on the user's rules + standard confed intuition.
    """
    # Rule (2): if router3 is configured as external peer, only establish under given condition.
    if is_external_peer_r3:
        if (r2.asn != r3.asn) or (_same_confed(r2, r3) and (r2.sub_as != r3.sub_as)):
            return "EBGP"  # treat as external-facing behavior
        return "NONE"

    # Otherwise, treat as internal peering if plausible.
    if _same_confed(r2, r3):
        return "IBGP" if (r2.sub_as == r3.sub_as) else "CONFED_EBGP"
    if (not r2.in_confed) and (not r3.in_confed) and (r2.asn == r3.asn):
        return "IBGP"
    # r2 is in a confederation and either:
    # - r3 is not in any confederation, OR
    # - r3 is in a different confederation (different confed identifier)
    # -> EBGP to external AS (AS path should carry the confederation identifier)
    if r2.in_confed and (not r3.in_confed or r2.asn != r3.asn):
        return "EBGP"
    # Not same AS/confed and not marked external => no session in this simplified model
    return "NONE"

def _to_padded_arrays(path: List[int], is_sub: List[int], path_len: int) -> Tuple[List[int], List[int]]:
    path2 = path[:path_len] + [0] * max(0, path_len - len(path))
    sub2  = is_sub[:path_len] + [0] * max(0, path_len - len(is_sub))
    return path2, sub2

def simulate_bgp_confederation(testcase: Dict[str, Any], path_len: int = 16, default_localpref: int = 100) -> Dict[str, Any]:
    """
    Input format (example):
    {
        "originAS": 65535,
        "router2": {"asNumber": 512, "subAS": 256},
        "router3": {"asNumber": 768, "subAS": 512},
        "removePrivateAS": true,
        "replaceAS": true,
        "localPref": 50,
        "isExternalPeer": false
    }

    Returns a dict containing installed RIB info for R2 and R3, including:
      - isRIB2/isRIB3
      - aspath2/aspath3 as strings
      - plus arrays aspath2_arr/isSubAS2_arr/aspath3_arr/isSubAS3_arr (0-padded on right)
      - plus localPref2/localPref3
    """
    origin_as = int(testcase["originAS"])
    r2 = RouterConf(int(testcase["router2"]["asNumber"]), int(testcase["router2"].get("subAS", 0)))
    r3 = RouterConf(int(testcase["router3"]["asNumber"]), int(testcase["router3"].get("subAS", 0)))

    remove_private = bool(testcase.get("removePrivateAS", False))
    replace_as     = bool(testcase.get("replaceAS", False))
    localpref_cfg  = int(testcase.get("localPref", default_localpref))
    is_external_r3 = bool(testcase.get("isExternalPeer", False))

    # ----------------------------
    # 1) Origin -> R2 (assume it arrives and installs)
    # ----------------------------
    isRIB2 = True
    # Standard BGP: origin advertises its own AS in AS_PATH; receiver does not prepend on receive.
    aspath2 = [origin_as]
    isSub2  = [0]
    localPref2 = localpref_cfg  # "R2 sets the given local preference value"

    # ----------------------------
    # 2) R2 -> R3 session decision
    # ----------------------------
    sess = _session_type_r2_r3(r2, r3, is_external_r3)
    if sess == "NONE":
        return {
            "isRIB2": True,
            "aspath2": " ".join(str(x) for x in aspath2),
            "isRIB3": False,
            "aspath3": "",
            # extras (useful for your harness; drop if you want strict minimal output)
            "localPref2": localPref2,
            "localPref3": None,
            "aspath2_arr": _to_padded_arrays(aspath2, isSub2, path_len)[0],
            "isSubAS2_arr": _to_padded_arrays(aspath2, isSub2, path_len)[1],
            "aspath3_arr": [0] * path_len,
            "isSubAS3_arr": [0] * path_len,
        }

    # ----------------------------
    # 3) Build update from R2 to R3 (modify AS_PATH + LOCAL_PREF according to rules)
    # ----------------------------
    out_path = aspath2[:]
    out_sub  = isSub2[:]

    # Rule (3): remove private ASNs before forwarding (optionally replace-as)
    if remove_private:
        # Choose replacement ASN if replaceAS is enabled.
        # - If R2 is in a confed, replacement depends on whether we're sending "outside confed".
        #   We'll decide later; for now, use the member AS (subAS) as the intra-confed identity.
        # - If not in confed, use r2.asn.
        provisional_repl = r2.sub_as if r2.in_confed else r2.asn

        new_path, new_sub = [], []
        for a, s in zip(out_path, out_sub):
            if _is_private_asn(a):
                if replace_as:
                    new_path.append(provisional_repl)
                    new_sub.append(1 if (r2.in_confed and provisional_repl == r2.sub_as) else 0)
                # else: drop it
            else:
                new_path.append(a)
                new_sub.append(s)
        out_path, out_sub = new_path, new_sub

    # Prepend rules when advertising:
    # - IBGP: do not prepend own AS
    # - CONFED_EBGP (inside same confed but different subAS): prepend own subAS, mark as subAS
    # - EBGP (outside AS/confed): prepend own "real" AS. If in confed, see rule (5).
    if sess == "CONFED_EBGP":
        out_path = [r2.sub_as] + out_path
        out_sub  = [1] + out_sub
        # LOCAL_PREF is allowed to be shared within a confed
        localPref3 = localPref2
    elif sess == "IBGP":
        # No AS prepend
        localPref3 = localPref2
    else:  # "EBGP"
        # Rule (5): advertising to a peer outside the confederation:
        # remove all sub-ASNs in the path and replace them with the confed number (asNumber).
        if r2.in_confed:
            # Strip any subAS-marked elements (confed-internal segments)
            stripped_path = [a for a, s in zip(out_path, out_sub) if s == 0]
            # Replace with confed identifier (prepend)
            out_path = [r2.asn] + stripped_path
            out_sub  = [0] + [0] * len(stripped_path)
        else:
            out_path = [r2.asn] + out_path
            out_sub  = [0] + out_sub

        # LOCAL_PREF is not exchanged across true external AS boundaries
        localPref3 = default_localpref

    # ----------------------------
    # 4) R3 receives and installs (assume best path)
    # ----------------------------
    isRIB3 = True
    aspath3 = out_path
    isSub3  = out_sub

    # Make arrays right-padded with zeros (rule 4)
    aspath2_arr, isSub2_arr = _to_padded_arrays(aspath2, isSub2, path_len)
    aspath3_arr, isSub3_arr = _to_padded_arrays(aspath3, isSub3, path_len)

    return {
        "isRIB2": isRIB2,
        "aspath2": " ".join(str(x) for x in aspath2),
        "isRIB3": isRIB3,
        "aspath3": " ".join(str(x) for x in aspath3)
    }
