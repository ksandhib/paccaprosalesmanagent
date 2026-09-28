import re
import json
import requests
import os
from datetime import date
from sqlalchemy.orm import Session
from backend.models import Report, Complaint, Collection, Sales
from backend.utils import logger

class ChatService:
    def __init__(self):
        # Load settings from config/config.json and .env if available
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config", "config.json"))
        self.ollama_url = "http://localhost:11434"
        self.ollama_model = "qwen2.5:14b"

        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    cfg = json.load(f)
                    self.ollama_url = cfg.get("ollama_url", self.ollama_url)
                    self.ollama_model = cfg.get("ollama_model", self.ollama_model)
            except:
                pass

        # Fallback check for .env
        from dotenv import load_dotenv
        load_dotenv()
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", self.ollama_url)
        self.ollama_model = os.getenv("OLLAMA_MODEL", self.ollama_model)

    def process_message(self, db: Session, message: str) -> str:
        """
        Processes a chat query. Matches user intents with database actions
        to return dynamic responses based on live database records.
        """
        msg_lower = message.lower()
        today_str = date.today().strftime("%Y-%m-%d")

        # 1. Intent: Complaints
        if "complaint" in msg_lower:
            complaints = db.query(Complaint).join(Report).all()
            if not complaints:
                return "There are no complaints registered in the system right now."
            
            reply = "Here are the registered complaints in the system:\n\n"
            reply += "| Rep | Client | Complaint Details | Severity | Status |\n"
            reply += "| --- | --- | --- | --- | --- |\n"
            for c in complaints:
                reply += f"| {c.report.representative} | {c.report.client_name} | {c.description} | **{c.severity}** | `{c.status}` |\n"
            return reply

        # 2. Intent: Today's reports
        if "today's reports" in msg_lower or "reports today" in msg_lower:
            reports = db.query(Report).filter(Report.date == today_str).all()
            if not reports:
                return f"No reports have been submitted today ({today_str}) yet."
            
            reply = f"Here are the reports submitted today ({today_str}):\n\n"
            reply += "| Rep | Client | Summary | Sentiment | Priority |\n"
            reply += "| --- | --- | --- | --- | --- |\n"
            for r in reports:
                reply += f"| {r.representative} | {r.client_name} | {r.summary or 'No summary'} | {r.sentiment} | {r.priority} |\n"
            return reply

        # 3. Intent: Today's collections or list collections
        if "collection" in msg_lower:
            collections = db.query(Collection).join(Report).all()
            if "today" in msg_lower:
                collections = [c for c in collections if c.report.date == today_str]
                
            if not collections:
                return "No payment collections were found matching your request."
                
            reply = "Here is the summary of payment collections:\n\n"
            reply += "| Rep | Client | Amount | Method | Reference |\n"
            reply += "| --- | --- | --- | --- | --- |\n"
            total = 0.0
            for c in collections:
                total += c.amount_collected
                reply += f"| {c.report.representative} | {c.report.client_name} | INR {c.amount_collected:,.2f} | {c.payment_method or 'N/A'} | {c.reference_no or 'N/A'} |\n"
            reply += f"\n**Total Collected: INR {total:,.2f}**"
            return reply

        # 4. Intent: Balaji's clients/reports or Suresh's reports
        for name in ["balaji", "suresh", "kumar"]:
            if name in msg_lower:
                reports = db.query(Report).filter(
                    (Report.representative.ilike(f"%{name}%")) | 
                    (Report.client_name.ilike(f"%{name}%"))
                ).all()
                
                if not reports:
                    return f"I couldn't find any reports matching '{name}'."
                
                reply = f"Here are the sales records matching **{name.capitalize()}**:\n\n"
                reply += "| Date | Rep | Client | Key Actions / Summary | Sentiment |\n"
                reply += "| --- | --- | --- | --- | --- |\n"
                for r in reports:
                    reply += f"| {r.date} | {r.representative} | {r.client_name} | {r.summary} | {r.sentiment} |\n"
                return reply

        # 5. Intent: Compare monthly/yearly performance
        if "compare" in msg_lower or "performance" in msg_lower:
            sales_data = db.query(Sales).join(Report).all()
            if not sales_data:
                return "There is no sales performance data to compare yet. Please upload reports."
            
            rep_performance = {}
            for s in sales_data:
                rep = s.report.representative
                rep_performance[rep] = rep_performance.get(rep, 0.0) + s.amount
                
            reply = "Here is the sales performance comparison by Representative:\n\n"
            reply += "| Sales Representative | Cumulative Booked Sales |\n"
            reply += "| --- | --- |\n"
            for rep, total in sorted(rep_performance.items(), key=lambda x: x[1], reverse=True):
                reply += f"| **{rep}** | INR {total:,.2f} |\n"
            return reply

        # 6. Call Local Ollama LLM for intelligent assistant fallback
        try:
            # Query recent 15 reports for database context
            recent_reports = db.query(Report).order_by(Report.id.desc()).limit(15).all()
            context_list = []
            for r in recent_reports:
                context_list.append(f"- Rep: {r.representative}, Client: {r.client_name}, Date: {r.date}, Summary: {r.summary}, Sentiment: {r.sentiment}, Priority: {r.priority}")
            
            db_context = "\n".join(context_list)
            
            prompt = f"""You are PaccaPro AI, an offline sales assistant with access to the local SQLite database.
Answer the user's query intelligently based on the following context of recent sales reports.

Recent Reports Context:
{db_context}

User Query: {message}

Return a concise and helpful response formatted in markdown. If the context does not contain enough details, answer as best as you can based on general sales management practices.
"""
            logger.info(f"Querying Ollama chat fallback model {self.ollama_model}...")
            response = requests.post(
                f"{self.ollama_url.rstrip('/')}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120.0
            )
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except Exception as e:
            logger.error(f"Chat service Ollama fallback failed: {str(e)}")

        # Heuristic conversational fallback
        return (
            f"Hello! I am your PaccaPro AI Assistant. I operate offline and have direct access to your local SQLite sales data.\n\n"
            f"Here are some examples of what you can ask me:\n"
            f"- *'Show today's reports'* (checks reports submitted on {today_str})\n"
            f"- *'List all collections'* (summarizes client payment records)\n"
            f"- *'Show Balaji's clients'* (filters by representative or client name)\n"
            f"- *'Show all complaints'* (displays unresolved client complaints)\n"
            f"- *'Compare performance'* (calculates sales performance by rep)\n\n"
            f"Please let me know how I can help you analyze the sales data!"
        )
