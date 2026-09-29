"""
ReliefChain AI - Main Entry Point.
Delegates to modular application in app.main while preserving full backward compatibility.
"""

from app.main import app, create_application

if __name__ == "__main__":
    import uvicorn
    from app.core.config import PORT
    uvicorn.run("app.main:app", host="127.0.0.1", port=PORT, reload=True)
