import google.generativeai as genai

API_KEY = "AIzaSyBuoUeHmP3ld2WJjcsdTsFY6-aZf2XXW4Q"
genai.configure(api_key=API_KEY)

with open("models.txt", "w") as f:
    try:
        models = genai.list_models()
        for m in models:
            f.write(f"{m.name}\n")
        print("Models saved to models.txt")
    except Exception as e:
        f.write(f"Error: {e}\n")
        print(f"Error: {e}")
AIzaSyBuoUeHmP3ld2WJjcsdTsFY6-aZf2XXW4Q
Siri@12345
srilakshmivedururi2310@gmail.com

AIzaSyDqPXhCUP4aJCZtdNOI6TOGagY9qVYXmXo



    "contact_info": {
        "email": "harikiranreddy2004.com",
        "linkedin": "/linkedinHarikiranreddy yarasani",
        "phone": "+91 7075669901"
    },
    "education": [
        {
            "degree": "Bachelor of Technology in Computer Science and Engineering",
            "details": "CGPA: 6.58",
            "institution": "CMR INSTITUE of Technology, Hyderabad, India",
            "years": "Expected Graduation: July 2026"
        },
        {
            "degree": "Intermediate (12th Grade)",
            "details": "Percentage: 89.1",
            "institution": "Narayana Iit Aceadmy",
            "years": null
        },
        {
            "degree": "(10th Grade)",
            "details": "Percentage: 100",
            "institution": "Narayana Group Of Schools",
            "years": null
        }
    ],
    "experience": [],
    "full_name": "Y.Harikiranreddy",
    "projects": [
        {
            "description": "Conducted an analytical study focused on identifying and predicting behavioral changes in students with specialized educational needs using data-driven methodologies. Utilized statistical analysis and behavioral modeling to support early intervention strategies and enhance individualized educational planning. Collaborated with educators and psychologists to interpret findings and ensure practical application in special education settings.",
            "name": "Predicting behavior change in students with specialized educational needs"
        }
    ],
    "skills": {
        "programming_languages": [
            "Python",
            "Java"
        ],
        "soft_skills": [
            "Teamwork",
            "Communication",
            "Time Management",
            "Solving",
            "Adaptability"
        ],
        "web_technologies": [
            "HTML",
            "CSS"
        ]
    },
    "summary": "Motivated Computer Science student with strong skills in , HTML,CSS, python, and web development. Seeking an opportunity to apply technical expertise and problem-solving abilities to contribute to innovative projects and support organizational success.. For details, click here."
}