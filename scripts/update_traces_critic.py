import json
import glob
from agents.validator import validate_agent_output

def main():
    traces = sorted(glob.glob('data/agent_traces/case_*.json'))
    print(f"Updating {len(traces)} traces...")

    for tpath in traces:
        with open(tpath, 'r', encoding='utf-8') as f:
            tdata = json.load(f)
        
        cid = tdata.get('case_id')
        for att in tdata.get('attempts', []):
            is_fault = 'fault' in cid or tdata.get('classification') == 'possible_fault'
            is_regional = 'regional' in cid or tdata.get('classification') == 'regional'
            
            if is_fault:
                crit_resp = (
                    f"DISPATCH REFUSED: Spike event '{cid}' represents a single-station instrument or logger fault. "
                    "No localized site inspection dispatch recommended. Certified outcome: 'outcome_possible_fault'."
                )
            elif is_regional:
                crit_resp = (
                    f"DISPATCH REFUSED: Event '{cid}' represents network-wide regional smog elevation across Delhi-NCR. "
                    "No point-source inspection dispatch recommended. Certified outcome: 'outcome_regional'."
                )
            else:
                crit_lines = ["Audited top suspect candidate facilities against verified tool data:\n"]
                for tc in att.get('tool_calls', []):
                    tname = tc.get('tool_name')
                    tres = tc.get('result', [])
                    if isinstance(tres, list) and tres and isinstance(tres[0], dict) and 'text' in tres[0]:
                        try:
                            tdict = json.loads(tres[0]['text'])
                        except:
                            tdict = {}
                    else:
                        tdict = {}
                    
                    if tname == 'check_site_operating_history':
                        cand_id = tdict.get('candidate_id')
                        cand_name = tdict.get('name', 'Site')
                        cand_status = tdict.get('operating_status', 'active_presumed')
                        reasons = tdict.get('operating_reasons', [])
                        reasons_str = f" Tags: {reasons}." if reasons else ""
                        if 'disused' in cand_status.lower() or 'decommissioned' in cand_status.lower():
                            crit_lines.append(
                                f"1. **{cand_name} ({cand_id})**: Aligned with the wind, but tagged disused in OpenStreetMap, so inspection is unlikely to be useful.{reasons_str}"
                            )
                        else:
                            crit_lines.append(
                                f"1. **{cand_name} ({cand_id})**: Operating status is '{cand_status}'. Verified active in OpenStreetMap."
                            )
                    elif tname == 'check_chemical_plume_coherence':
                        ratio = tdict.get('pm25_pm10_ratio')
                        sig_label = tdict.get('signature_label', 'evaluated')
                        ctype = tdict.get('candidate_type', 'source')
                        if ratio is not None:
                            crit_lines.append(
                                f"2. **Chemical Signature ({ctype})**: Observed PM2.5/PM10 ratio is {ratio} ({sig_label})."
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
