"""Core/api/main.py — Run Mr.Holmes REST API server."""
import uvicorn

def main(host="0.0.0.0", port=8000):
    print(f"Starting Mr.Holmes API on http://{host}:{port}")
    print("API docs: http://localhost:8000/docs")
    uvicorn.run("Core.api.server:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    main()
