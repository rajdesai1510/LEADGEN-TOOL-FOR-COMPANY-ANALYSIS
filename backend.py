import json
import os
import requests
import logging
import threading
import time
import re
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from phi.agent import Agent, RunResponse
from phi.model.groq import Groq
from phi.tools.firecrawl import FirecrawlTools

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Cache for company information
company_cache: Dict[str, Dict] = {}

app = FastAPI(title="Company Intelligence Chatbot")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: str

class CompanyRequest(BaseModel):
    url: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    company_name: Optional[str] = None
    is_processing: bool = False
    session_id: str

# Session storage
sessions: Dict[str, Dict] = {}

def is_url(text: str) -> bool:
    """Check if the input text is a URL."""
    url_pattern = re.compile(
        r'^(?:http|https)://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or ipv4
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(url_pattern.match(text))

def get_company_name(url: str) -> str:
    """Extract company name from URL using Firecrawl and LLM."""
    try:
        agent = Agent(
            instructions=["Provide just the name of the company and nothing else"],
            model=Groq(id="llama-3.3-70b-versatile", api_key="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"),
            tools=[FirecrawlTools(scrape=True, crawl=False, api_key="fc-28cbcb774ed6450687058c877f1d9cda")],
            show_tool_calls=False,
            markdown=True,
            system_message="Just give me the name of the company nothing else"
        )
        
        run: RunResponse = agent.run(f"Find the name of this company using this url: {url}")
        company_name = run.content.strip()
        logger.info(f"Extracted company name: {company_name} from URL: {url}")
        return company_name
    except Exception as e:
        logger.error(f"Error extracting company name: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to extract company name: {str(e)}")

def run_langflow_query(question: str, company_name: str) -> str:
    """Execute query with proper SerpAPI result handling"""
    try:
        from langchain_community.utilities import SerpAPIWrapper
        from langchain_groq import ChatGroq
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        # 1. Configure search with original parameters
        serp = SerpAPIWrapper(
            serpapi_api_key="<YOUR_SERP_API>",
            params={
                "engine": "google",
                "google_domain": "google.com",
                "gl": "US",
                "hl": "en",
                "num": 5
            }
        )

        # 2. Build search query
        search_query = f"{question} {company_name}"
        
        # 3. Get raw search results
        raw_results = serp.results(search_query)  # Returns dict directly
        
        # 4. Format results exactly like Langflow's ParseData component
        formatted_context = "\n".join(
            f"Title: {res.get('title','')[:100]}\n"
            f"Link: {res.get('link','')}\n"
            f"Snippet: {res.get('snippet','')[:100]}"
            for res in raw_results.get("organic_results", [])[:5]
        )

        # 5. Create final prompt matching Langflow's structure
        final_prompt = f"""Instructions:
        - Answer in 2-3 words max
        - Choose the most appropriate result if multiple answers exist
        - Say 'I DONT KNOW' if uncertain

        Company: {company_name}
        Question: {question}
        Context: {formatted_context}"""

        # 6. Get Groq response with original parameters
        groq_chat = ChatGroq(
            temperature=0.1,
            model_name="llama-3.3-70b-versatile",
            api_key="<YOUR_GROQ_API>",
            max_tokens=50
        )

        # 7. Process response like Langflow's TextOutput
        response = groq_chat.invoke(final_prompt).content
        clean_response = response.split("Answer:", 1)[-1].strip(' "\n')
        
        return clean_response if len(clean_response) > 2 else "I DONT KNOW"

    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        return "I DONT KNOW"

def process_company_url(url: str, session_id: str):
    """Process company URL in background."""
    try:
        company_name = get_company_name(url)
        sessions[session_id]["company_name"] = company_name
        sessions[session_id]["is_processing"] = False
        logger.info(f"Finished processing URL for session {session_id}")
    except Exception as e:
        logger.error(f"Error in background processing: {str(e)}")
        sessions[session_id]["is_processing"] = False
        sessions[session_id]["error"] = str(e)

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id
    message = request.message
    
    # Initialize session if not exists
    if session_id not in sessions:
        sessions[session_id] = {"history": [], "company_name": None, "is_processing": False}
    
    # Check if company is still being processed
    if sessions[session_id].get("is_processing", False):
        return ChatResponse(
            response="Still analyzing company website. Please wait a moment...",
            company_name=sessions[session_id].get("company_name"),
            is_processing=True,
            session_id=session_id
        )
    
    # If there was an error during company processing
    if "error" in sessions[session_id]:
        error = sessions[session_id].pop("error")
        return ChatResponse(
            response=f"Error analyzing company: {error}. Please try a different URL or question.",
            company_name=sessions[session_id].get("company_name"),
            is_processing=False,
            session_id=session_id
        )
    
    # Check if this is a URL
    if is_url(message):
        # Start background processing
        sessions[session_id]["is_processing"] = True
        background_task = threading.Thread(target=process_company_url, args=(message, session_id))
        background_task.start()
        
        return ChatResponse(
            response="Analyzing the company website... This might take a moment.",
            company_name=None,
            is_processing=True,
            session_id=session_id
        )
    
    # Check if this is the first message and appears to be a company name
    if not sessions[session_id].get("company_name") and message:
        # Assume message is a company name directly
        sessions[session_id]["company_name"] = message
        return ChatResponse(
            response=f"I'll answer questions about {message}. What would you like to know?",
            company_name=message,
            is_processing=False,
            session_id=session_id
        )
    
    # Handle questions about company if company_name is available
    company_name = sessions[session_id].get("company_name")
    if not company_name:
        return ChatResponse(
            response="Please provide a company name or website URL first.",
            company_name=None,
            is_processing=False,
            session_id=session_id
        )
    
    # Process question about company
    answer = run_langflow_query(message, company_name)
    
    # Update session history
    sessions[session_id]["history"].append({"question": message, "answer": answer})
    
    return ChatResponse(
        response=answer,
        company_name=company_name,
        is_processing=False,
        session_id=session_id
    )

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "company_name": sessions[session_id].get("company_name"),
        "is_processing": sessions[session_id].get("is_processing", False),
        "history": sessions[session_id].get("history", [])
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)