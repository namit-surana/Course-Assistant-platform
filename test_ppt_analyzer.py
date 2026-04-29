import os
import sys

sys.path.append(os.path.abspath("."))

from src.ppt_agent.ppt_analyzer import analyze_ppt

ppt_path = "sample_presentation.pptx"

rubric = [
    {
        "category": "Clarity",
        "max_score": 10,
        "description": "How clearly ideas are presented",
    },
    {
        "category": "Content",
        "max_score": 15,
        "description": "Depth and correctness of content",
    },
    {
        "category": "Design",
        "max_score": 5,
        "description": "Visual quality of slides",
    },
]

result = analyze_ppt(ppt_path, rubric)
print(result)
