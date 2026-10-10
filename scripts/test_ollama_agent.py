import os
import sys
import json
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from strands.models.ollama import OllamaModel
from agents.investigator import create_investigator_agent
from agents.critic import create_critic_agent
from agents.validator import validate_agent_output

model = OllamaModel(host="http://localhost:11434", model_id="llama3.2:latest")
inv = create_investigator_agent(model=model)

prompt = "Investigate case_anand_vihar_20251102. Retrieve telemetry and provide your assessment."
print("Invoking Investigator...")
start = time.time()
res = inv(prompt)
print(f"Investigator responded in {time.time() - start:.2f}s:")
print(res)
