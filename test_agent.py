from openai import OpenAI
import pandas as pd
import os
from dotenv import load_dotenv
import json
from datetime import datetime
import requests

load_dotenv()
client = OpenAI(api_key = os.getenv("OPENAI_API_KEY"),
                base_url = "https://api.deepseek.com")

class TestAgent:
    def __init__(self):
        self.blockchain_logger_url = "http://127.0.0.1:8000/log"
    
    def log_decision(self, reason: str,
                     action: str,
                     agent_id: str = "insight_agent",
        ):
        payload = {
            "agent_id": agent_id,
            "action": action,
            "reason": reason,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        try:
            res = requests.post(self.blockchain_logger_url, json = payload)
            res.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            print("📝 Log success:", res.json())
        except requests.exceptions.ConnectionError as e:
            print(f"🚨 Failed to connect to blockchain logger at {self.blockchain_logger_url}: {e}")
            print("   Please ensure blockchain_logger.py (FastAPI app) is running.")
        except requests.exceptions.RequestException as e:
            print(f"🚨 Failed to log to blockchain (HTTP Error): {e}")
            if res is not None:
                print(f"   Response content: {res.text}")
        except Exception as e:
            print(f"🚨 An unexpected error occurred during logging: {e}")
        
    def test_model(self, prompt: str):
        #print(f"[INFO] Testing model with prompt: {prompt}")
        response = client.chat.completions.create(
            model = "deepseek-chat",
            messages = [{"role": "user", "content": prompt}],
            response_format = {"type": "json_object"}
        )
        response_json = json.loads(response.choices[0].message.content)
        insight = response_json.get("insight", "")
        decision_log = response_json.get("log", {})

        self.log_decision(reason = decision_log.get("reason", ""),
                          action = decision_log.get("action", ""),
                          agent_id = decision_log.get("agent_id", "test_agent"),
                          )

        return insight

if __name__ == "__main__":
    test_agent = TestAgent()
    prompt = """
Explain a complex scientific concept in a way that is easy to understand.
This should be easy to understand for a 5 year old. Pick a new topic every time.

You are also to provide a reasons for your answer. Every step must have a reason and this reason should be logged.
Your output should be a JSON object with the following fields:
{
    "insight": string,
    "log":{ 
        "agent_id": insight_agent,
        'action': 'Generate insights from the best model and data',
        'reason': string,(you fill this with the reason for your decision)
    }
}
"""
    print("\n" + test_agent.test_model(prompt = prompt))