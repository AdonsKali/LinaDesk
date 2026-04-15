tools=[
        {
            "type": "function",
            "function": {
                "name": "powerShell",
                "description": "Execute powershell command.",
                "parameters": {
                    "type": 'object',
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "mk_file",
                "description": "Create file",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}, "data": {"type": "string"}},
                    "required": ["path", "data"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Search info by query in internet and gets website links",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
        },
        # {
        #     "type": "function",
        #     "function": {
        #         "name": "search_and_play",
        #         "description": "Search music/video on the youtube, soundcloud ... and playing it. In video only sound",
        #         "parameters": {
        #             "type": "object",
        #             "properties": {"query": {"type": "string"}},
        #             "required": ["query"],
        #         },
        #     },
        # }, 
        ]
