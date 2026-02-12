from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import re
import os

app = FastAPI()

# ------------------------------
# CORS
# ------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------
# Request Model
# ------------------------------
class CodeInput(BaseModel):
    code: str


# ------------------------------
# API ROUTES
# ------------------------------
@app.post("/review")
def review_code(input: CodeInput):
    code = input.code

    issues = []
    suggestions = []
    score = 10

    security_score = 10
    performance_score = 10
    maintainability_score = 10

    lines = code.split("\n")

    # 🔹 Long code
    if len(lines) > 20:
        issues.append({
            "message": "The overall code is long. Consider splitting it into smaller modules.",
            "line": 1
        })
        score -= 1
        maintainability_score -= 2

    # 🔹 Long functions
    for index, line in enumerate(lines):
        if line.strip().startswith("def "):
            start_line = index
            function_length = 0

            for j in range(index + 1, len(lines)):
                if lines[j].strip().startswith("def "):
                    break
                if lines[j].strip() != "":
                    function_length += 1

            if function_length > 10:
                issues.append({
                    "message": f"Function starting at line {start_line + 1} is too long ({function_length} lines).",
                    "line": start_line + 1
                })
                score -= 1
                maintainability_score -= 2

    # 🔹 Too many parameters
    for match in re.finditer(r"def\s+\w+\((.*?)\):", code):
        params = match.group(1)
        param_list = [p.strip() for p in params.split(",") if p.strip()]

        if len(param_list) > 4:
            issues.append({
                "message": f"Function has too many parameters ({len(param_list)}). Consider refactoring.",
                "line": 1
            })
            score -= 1
            maintainability_score -= 2

    # 🔹 Nested loops
    loop_lines = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("for ") or stripped.startswith("while "):
            loop_lines.append(index)

    if len(loop_lines) > 1:
        issues.append({
            "message": "Nested loops detected. This may impact performance.",
            "line": loop_lines[1] + 1
        })
        score -= 1
        performance_score -= 2

    # 🔹 eval detection
    for index, line in enumerate(lines):
        if "eval(" in line:
            issues.append({
                "message": "Use of eval() detected. This can lead to serious security vulnerabilities.",
                "line": index + 1
            })
            score -= 2
            security_score -= 3

    # 🔹 Hardcoded password
    for index, line in enumerate(lines):
        if re.search(r"password\s*=\s*['\"].+['\"]", line, re.IGNORECASE):
            issues.append({
                "message": "Hardcoded password detected. Avoid storing credentials directly in code.",
                "line": index + 1
            })
            score -= 2
            security_score -= 3

    # 🔹 Complexity
    if code.count("if ") > 3:
        suggestions.append("Too many conditional branches. Consider simplifying logic.")
        maintainability_score -= 1

    # 🔹 Error handling
    if "try:" not in code and "except" not in code:
        suggestions.append("You should add proper error handling using try and except blocks.")
        maintainability_score -= 1

    # 🔹 Comment check
    if "#" not in code:
        suggestions.append("Add comments to improve readability.")
        maintainability_score -= 1

    # Prevent negatives
    score = max(score, 0)
    security_score = max(security_score, 0)
    performance_score = max(performance_score, 0)
    maintainability_score = max(maintainability_score, 0)

    # AI Feedback
    ai_feedback = "Based on structural and security analysis, "

    if security_score < 7:
        ai_feedback += "there are potential security vulnerabilities that should be addressed immediately. "

    if performance_score < 7:
        ai_feedback += "performance may degrade with large datasets due to inefficient logic. "

    if maintainability_score < 7:
        ai_feedback += "code structure could benefit from modularization and better separation of concerns. "

    if score >= 9:
        ai_feedback = "Your code demonstrates strong structure and safe programming practices."

    ai_feedback += " Improving these areas will make the application more scalable and production-ready."

    # Human Explanation
    if issues or suggestions:
        explanation = "After reviewing your code, here are my observations. "

        for issue in issues:
            explanation += issue["message"] + " "

        for suggestion in suggestions:
            explanation += suggestion + " "

        explanation += "Addressing these points will significantly improve overall quality."
    else:
        explanation = "Your code looks clean, readable, and well structured. Great job!"

    return {
        "score": score,
        "security_score": security_score,
        "performance_score": performance_score,
        "maintainability_score": maintainability_score,
        "issues": issues,
        "suggestions": suggestions,
        "explanation": explanation,
        "ai_feedback": ai_feedback
    }


# ------------------------------
# SERVE REACT BUILD
# ------------------------------

if os.path.exists("build"):
    app.mount("/static", StaticFiles(directory="build/static"), name="static")

    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        return FileResponse("build/index.html")
