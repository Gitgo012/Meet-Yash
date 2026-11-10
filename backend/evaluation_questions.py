TEST_CASES = [

    {
        "question": "Tell me about your education.",
        "expected_facts": [
            "B.Tech",
            "Computer Science",
            "NIIT University"
        ]
    },

    {
        "question": "What did you do at Prodigy Infotech?",
        "expected_facts": [
            "Generative AI",
            "GPT-2",
            "Stable Diffusion"
        ]
    },

    {
        "question": "Tell me about your XCaliber experience.",
        "expected_facts": [
            "Java",
            "Temporal",
            "Go",
            "platform engineering"
        ]
    },

    {
        "question": "What is your biggest strength?",
        "expected_facts": [
            "learning by building",
            "practical implementation"
        ]
    },

    {
        "question": "Tell me about a specific professional failure.",
        "must_not_invent": True
    },

    {
        "question": "What misconception do your coworkers have about you?",
        "must_not_invent": True
    }
]