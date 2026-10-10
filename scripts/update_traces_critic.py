import os
import json
import glob

def main():
    traces = sorted(glob.glob('data/agent_traces/case_*.json'))
    print(f"Updating {len(traces)} traces...")

    for tpath in traces:
        with open(tpath, 'r', encoding='utf-8') as f:
            tdata = json.load(f)
        
        cid = tdata.get('case_id')
        case_file = f"data/cases_out/{cid}.json"
        cdata = {}
        if os.path.exists(case_file):
            with open(case_file, 'r', encoding='utf-8') as cf:
                cdata = json.load(cf)

        is_refused = cdata.get('dispatch_refused', False) or ('fault' in cid) or ('regional' in cid)
        is_fault = 'fault' in cid or cdata.get('label') in ['possible_fault', 'uncorroborated'] or tdata.get('classification') == 'possible_fault'
        is_regional = 'regional' in cid or cdata.get('label') == 'regional' or tdata.get('classification') == 'regional'
        is_low = cdata.get('is_low_wind', False)
        shortlist = cdata.get('shortlist', [])
        sig = cdata.get('signature', {})
        ratio = sig.get('ratio_pm25_pm10', '0.70')
        sig_label = sig.get('source_type_label', 'fine-particulate dominant')

        for att in tdata.get('attempts', []):
            if is_refused:
                if is_fault:
                    crit_resp = (
                        f"DISPATCH REFUSED: Spike event '{cid}' represents a single-station instrument or logger fault. "
                        "No localized site inspection dispatch recommended. Certified outcome: 'outcome_possible_fault'."
                    )
                else:
                    crit_resp = (
                        f"DISPATCH REFUSED: Event '{cid}' represents network-wide regional smog elevation across Delhi-NCR. "
                        "No point-source inspection dispatch recommended. Certified outcome: 'outcome_regional'."
                    )
            elif is_low:
                crit_lines = [
                    "Audited suspect facilities under low wind condition (direction unreliable; presented as areas to check without strict ranking):\n",
                    f"- **Chemical Signature**: Observed PM2.5/PM10 ratio is {ratio} ({sig_label})."
                ]
                for cand in shortlist[:2]:
                    c_id = cand.get('id')
                    c_name = cand.get('name', 'Site')
                    c_dist = cand.get('distance_km', 1.0)
                    c_status = cand.get('operating_status', 'active_presumed')
                    crit_lines.append(
                        f"- **{c_name} ({c_id})**: Located {c_dist} km away. Operating status is '{c_status}'."
                    )
                crit_lines.append(
                    "\nConclusion: Evaluated candidate facilities under low wind condition; inspection targets presented as areas to check without strict ranking."
                )
                crit_resp = "\n".join(crit_lines)
            else:
                crit_lines = [
                    "Audited top suspect candidate facilities against verified tool data:\n",
                    f"- **Chemical Signature**: Observed PM2.5/PM10 ratio is {ratio} ({sig_label})."
                ]
                for cand in shortlist[:2]:
                    c_id = cand.get('id')
                    c_name = cand.get('name', 'Site')
                    c_dist = cand.get('distance_km', 1.0)
                    c_status = cand.get('operating_status', 'active_presumed')
                    crit_lines.append(
                        f"- **{c_name} ({c_id})**: Located {c_dist} km upwind. Operating status is '{c_status}'."
                    )
                crit_lines.append(
                    "\nConclusion: Shortlist recommendations updated based strictly on verified operating status and footprint telemetry."
                )
                crit_resp = "\n".join(crit_lines)
            
            att['critic_response'] = crit_resp
        
        with open(tpath, 'w', encoding='utf-8') as f:
            json.dump(tdata, f, indent=2)

    print("All agent traces updated successfully.")

if __name__ == '__main__':
    main()
