from app.worker.analyzers.ppt_analyzer import analyze_ppt

# 👇 give correct path to your ppt file
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

print("\n===== RESULT =====\n")
print(result)
