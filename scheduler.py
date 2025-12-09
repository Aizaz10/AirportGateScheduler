import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Any

# -------------------------
# Utility helpers
# -------------------------
def to_dt(x: Any) -> pd.Timestamp:
    # robust datetime parse
    return pd.to_datetime(x)

def normalize(s: str) -> str:
    return str(s).strip().lower()

def aircraft_matches(compat_list: List[str], aircraft: str) -> bool:
    # match case-insensitive, allow substrings (A320 matches A320neo)
    a = normalize(aircraft)
    for comp in compat_list:
        c = normalize(comp)
        if c == "all":
            return True
        if c == a or c in a or a in c:
            return True
    return False

def intervals_overlap(s1: pd.Timestamp, e1: pd.Timestamp, s2: pd.Timestamp, e2: pd.Timestamp) -> bool:
    return max(s1, s2) < min(e1, e2)

# -------------------------
# Main scheduler function
# -------------------------
def schedule_flights(flights_df: pd.DataFrame, gates_df: pd.DataFrame, post_buffer_min: int = 0, pre_buffer_min: int = 0) -> pd.DataFrame:
    
    # copy to avoid mutation
    flights = flights_df.copy()
    gates = gates_df.copy()

    # parse datetimes
    flights['arrival'] = flights['arrival'].apply(to_dt)
    flights['departure'] = flights['departure'].apply(to_dt)

    # normalize columns
    flights['priority'] = flights.get('priority', 2).astype(int)
    flights['country_type'] = flights['country_type'].fillna('domestic').apply(lambda x: normalize(x))
    gates['country_type'] = gates['country_type'].fillna('mixed').apply(lambda x: normalize(x))
    gates['gate_type'] = gates.get('gate_type', 'contact').apply(lambda x: normalize(x))
    gates['is_remote_gate'] = gates['is_remote_gate'].astype(str).apply(lambda x: x.strip().lower() in ('yes','y','1','true','t'))

    # prepare compatible lists
    def parse_compat(x):
        if pd.isna(x):
            return ['all']
        # allow comma or pipe separated
        s = str(x)
        if '|' in s:
            parts = [p.strip() for p in s.split('|') if p.strip()]
        else:
            parts = [p.strip() for p in s.split(',') if p.strip()]
        return parts if parts else ['all']

    gates['compatible_list'] = gates['compatible_aircraft'].apply(parse_compat)

    # Sort flights by priority then arrival
    flights = flights.sort_values(by=['priority', 'arrival']).reset_index(drop=True)

    # gate schedules: dict gate_id -> list of (start,end)
    gate_schedule: Dict[str, List[Tuple[pd.Timestamp, pd.Timestamp]]] = {gid: [] for gid in gates['gate_id']}

    # helper to find candidate gates (non-remote first)
    gates_order = list(gates['gate_id'])

    assigned = []
    for _, f in flights.iterrows():
        fid = f['flight_id']
        aircraft = f['aircraft_type']
        arr = f['arrival'] - pd.Timedelta(minutes=pre_buffer_min)
        dep = f['departure'] + pd.Timedelta(minutes=post_buffer_min) + pd.Timedelta(minutes=int(f.get('turnaround_minutes', 0)))
        f_country = normalize(f.get('country_type', 'domestic'))
        f_priority = int(f.get('priority', 2))

        chosen_gate = None

        # Prefer non-remote gates first (terminal/contact)
        non_remote = [g for g in gates_order if not gates.loc[gates['gate_id'] == g, 'is_remote_gate'].values[0]]
        remote = [g for g in gates_order if gates.loc[gates['gate_id'] == g, 'is_remote_gate'].values[0]]

        def try_list(candidate_gates: List[str]) -> str:
            best = None
            best_free_time = None
            for g in candidate_gates:
                row = gates[gates['gate_id'] == g].iloc[0]
                compat = row['compatible_list']
                gate_country = normalize(row['country_type'])
                # priority rule: if flight is priority 1 and gate is remote (or not terminal) skip -> we rely on is_remote flag
                # country rule:
                if f_country == 'international' and gate_country != 'international' and gate_country != 'mixed':
                    continue
                if f_country == 'domestic' and gate_country not in ('domestic','international','mixed'):
                    continue
                # aircraft compatibility
                if not aircraft_matches(compat, aircraft):
                    continue
                # check no overlap
                busy = False
                for (s,e) in gate_schedule[g]:
                    if intervals_overlap(s,e,arr,dep):
                        busy = True
                        break
                if busy:
                    continue
                # choose gate with earliest last end (tie-break)
                last_end = max([pd.Timestamp.min] + [e for (s,e) in gate_schedule[g]])
                if best is None or last_end < best_free_time:
                    best = g
                    best_free_time = last_end
            return best

        chosen_gate = try_list(non_remote)
        if chosen_gate is None:
            chosen_gate = try_list(remote)

        if chosen_gate:
            gate_schedule[chosen_gate].append((arr, dep))
            status = "assigned"
        else:
            chosen_gate = "Unassigned"
            status = "unassigned"

        assigned.append({
            "flight_id": fid,
            "airline": f.get('airline', ''),
            "aircraft_type": aircraft,
            "arrival": f['arrival'],
            "departure": f['departure'],
            "turnaround_minutes": f.get('turnaround_minutes', ''),
            "priority": f_priority,
            "country_type": f_country,
            "assigned_gate": chosen_gate,
            "status": status
        })

    out = pd.DataFrame(assigned)
    # sort by arrival for display
    out = out.sort_values(by='arrival').reset_index(drop=True)
    return out
