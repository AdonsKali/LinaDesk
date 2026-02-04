tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "cmd",
                            "description": "Execute cmd command (paths in quotes)",
                            "parameters": {
                                "properties": {"command": {"type": "string"}},
                                "required": ["command"],
                            },
                        },
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "open",
                            "description": "open in browser link",
                            "parameters": {
                                "type": "object",
                                "properties": {"path": {"type": "string"}},
                                "required": ["path"],
                            },
                        },
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "shell",
                            "description": "Execute power shell command",
                            "parameters": {
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
                                "properties": {"query": {"type": "string"}},
                                "required": ["query"],
                            },
                        },
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "list_directory",
                            "description": "Get list of directories",
                            "parameters": {
                                "type": "object",
                                "properties": {"path": {"type": "string"}},
                            },
                        },
                    },
        ]
